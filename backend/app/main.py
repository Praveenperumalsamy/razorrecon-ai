"""
RazorRecon AI — Main FastAPI Application

Production REST API for autonomous financial reconciliation controller.

Security posture:
- JWT auth + role-based access control (admin / reviewer / viewer) on every
  data-bearing endpoint.
- CORS restricted to configured origins (never '*' in production).
- Rate limiting on auth endpoints and globally.
- Structured JSON request logging with correlation IDs; no secrets logged.
- Immutable, DB-persisted audit trail (survives restarts, visible across
  all workers) instead of the original in-memory-only log.
- Global exception handler that never leaks stack traces to clients.
"""

import io
import json
import logging
import os
import time
import uuid
from typing import Optional, List, Dict, Any

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db, check_db_connection
from app.deps import get_current_user, require_min_role
from app.logging_config import configure_logging
from app.models.db_models import UserDB
from app.rate_limit import limiter
from app.routers import auth as auth_router
from app.routers import webhooks as webhooks_router
from app.services.ai_analyst import ReconciliationAnalyst
from app.services.audit import AuditLogger
from app.services.chat import FinanceController
from app.services.evaluation import EvaluationEngine
from app.services.exceptions import ExceptionManager
from app.services.reconciliation import ReconciliationEngine

configure_logging()
logger = logging.getLogger("razorrecon.api")

if settings.SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.APP_ENV, traces_sample_rate=0.1)

app = FastAPI(
    title=f"{settings.APP_NAME} — AI Finance Controller API",
    description="Autonomous financial reconciliation controller with precision-first confidence gates and audit trails.",
    version=settings.APP_VERSION,
    docs_url="/docs" if not settings.is_production else None,  # hide Swagger UI in prod
    redoc_url="/redoc" if not settings.is_production else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restricted to explicitly configured origins, never wildcard in prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attaches a request ID for log correlation and adds security headers."""
    request_id = str(uuid.uuid4())[:12]
    start = time.time()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = round((time.time() - start) * 1000, 1)
        status_code = response.status_code if response else 500
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
        if response is not None:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            if settings.is_production:
                response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak internal stack traces / details to API clients."""
    logger.exception("unhandled_exception", extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. It has been logged for investigation."},
    )


app.include_router(auth_router.router)
app.include_router(webhooks_router.router)

# --- Long-lived, stateless singletons ---
# The AI analyst wraps a stateless LLM client and is safe to share.
# Evaluation engine and chat controller are similarly stateless helpers.
ai_analyst = ReconciliationAnalyst()
eval_engine = EvaluationEngine()
chat_controller = FinanceController(ai_analyst)

RECON_CONFIG = {
    "AUTO_RECONCILE_THRESHOLD": settings.AUTO_RECONCILE_THRESHOLD,
    "AI_REVIEW_THRESHOLD": settings.AI_REVIEW_THRESHOLD,
    "DATE_TOLERANCE_DAYS": settings.DATE_TOLERANCE_DAYS,
}

# In-memory cache of the most recently computed reconciliation result and
# uploaded source dataframes. NOTE: this is process-local. Running more than
# one uvicorn/gunicorn worker means each worker has its own cache; the
# durable, cross-worker source of truth is the DB-persisted audit_log and
# exceptions tables. For true multi-worker cache consistency, back this with
# Redis or object storage (see PRODUCTION.md) — flagged here rather than
# silently assumed.
_state: Dict[str, Any] = {"dfs": {}, "last_results": None}

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _build_engine(db: Session) -> ReconciliationEngine:
    audit_logger = AuditLogger(db)
    exception_manager = ExceptionManager(db, audit_logger)
    return ReconciliationEngine(
        config=RECON_CONFIG,
        audit_logger=audit_logger,
        exception_manager=exception_manager,
        ai_analyst=ai_analyst,
    )


def _load_default_synthetic_data(db: Session) -> Dict[str, Any]:
    """
    Loads bundled synthetic fixtures for local dev / demo mode ONLY.
    Never called automatically in production (see startup_event) — real
    deployments should ingest via /api/upload (CSV) or the Razorpay live
    integration (/api/webhooks/razorpay + a scheduled settlement pull).
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic"))
    try:
        if os.path.exists(os.path.join(base_dir, "bank_transactions_dev.csv")):
            _state["dfs"]["bank"] = pd.read_csv(os.path.join(base_dir, "bank_transactions_dev.csv"))
            _state["dfs"]["settlement"] = pd.read_csv(os.path.join(base_dir, "razorpay_settlements_dev.csv"))
            _state["dfs"]["ledger"] = pd.read_csv(os.path.join(base_dir, "internal_ledger_dev.csv"))
            _state["dfs"]["refund"] = pd.read_csv(os.path.join(base_dir, "refunds_dev.csv"))
            _state["dfs"]["chargeback"] = pd.read_csv(os.path.join(base_dir, "chargebacks_dev.csv"))
            engine = _build_engine(db)
            results = engine.run(
                _state["dfs"]["bank"],
                _state["dfs"]["settlement"],
                _state["dfs"]["ledger"],
                _state["dfs"].get("refund"),
                _state["dfs"].get("chargeback"),
            )
            _state["last_results"] = results
            logger.info("demo_dataset_loaded")
    except Exception as e:
        logger.warning("demo_dataset_load_failed", extra={"error": str(e)})
    return _state.get("last_results") or {}


@app.on_event("startup")
def startup_event():
    init_db()  # safety net; Alembic migrations are the source of truth in prod
    logger.info("startup", extra={"env": settings.APP_ENV, "version": settings.APP_VERSION})
    if not settings.is_production:
        from app.database import session_scope

        with session_scope() as db:
            _load_default_synthetic_data(db)


# --- Health checks (no auth — used by load balancers / k8s probes) ---


@app.get("/")
def read_root():
    return {"app": settings.APP_NAME, "status": "healthy", "version": settings.APP_VERSION}


@app.get("/health/live")
def liveness():
    """Process is up. Does not check dependencies."""
    return {"status": "alive"}


@app.get("/health/ready")
def readiness():
    """Process is up AND its dependencies (DB) are reachable."""
    db_ok = check_db_connection()
    if not db_ok:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ready", "database": "connected"}


# --- Data ingestion ---


@app.post("/api/upload")
async def upload_files(
    bank_file: Optional[UploadFile] = File(None),
    settlement_file: Optional[UploadFile] = File(None),
    ledger_file: Optional[UploadFile] = File(None),
    refund_file: Optional[UploadFile] = File(None),
    chargeback_file: Optional[UploadFile] = File(None),
    _user: UserDB = Depends(require_min_role("reviewer")),
):
    """POST /api/upload — Ingest CSV datasets and validate. Requires reviewer+ role."""
    summary = {}

    async def _read_csv(f: UploadFile, key: str, label: str):
        content = await f.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"{label} exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV in {label}: {e}")
        _state["dfs"][key] = df
        summary[f"{key}_records"] = len(df)

    if bank_file:
        await _read_csv(bank_file, "bank", "bank_file")
    if settlement_file:
        await _read_csv(settlement_file, "settlement", "settlement_file")
    if ledger_file:
        await _read_csv(ledger_file, "ledger", "ledger_file")
    if refund_file:
        await _read_csv(refund_file, "refund", "refund_file")
    if chargeback_file:
        await _read_csv(chargeback_file, "chargeback", "chargeback_file")

    return {"status": "success", "summary": summary}


@app.post("/api/reconcile")
def run_reconciliation(db: Session = Depends(get_db), _user: UserDB = Depends(require_min_role("reviewer"))):
    """POST /api/reconcile — Run the 5-step reconciliation engine. Requires reviewer+ role."""
    if not all(k in _state["dfs"] for k in ("bank", "settlement", "ledger")):
        _load_default_synthetic_data(db)

    engine = _build_engine(db)
    results = engine.run(
        _state["dfs"].get("bank", pd.DataFrame()),
        _state["dfs"].get("settlement", pd.DataFrame()),
        _state["dfs"].get("ledger", pd.DataFrame()),
        _state["dfs"].get("refund", pd.DataFrame()),
        _state["dfs"].get("chargeback", pd.DataFrame()),
    )
    _state["last_results"] = results
    return _strip_dataframes(results)


@app.post("/api/demo")
def run_demo(db: Session = Depends(get_db), _user: UserDB = Depends(require_min_role("reviewer"))):
    """POST /api/demo — One-click demo mode processing the bundled synthetic dataset."""
    results = _load_default_synthetic_data(db)
    return _strip_dataframes(results)


def _strip_dataframes(results: Dict[str, Any]) -> Dict[str, Any]:
    """API responses should never try to JSON-serialize raw DataFrames."""
    if not results:
        return {}
    return {k: v for k, v in results.items() if k != "dataframes"}


# --- Read endpoints (any authenticated user) ---


@app.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db), _user: UserDB = Depends(get_current_user)):
    if not _state["last_results"]:
        run_reconciliation(db=db, _user=_user)
    return _state["last_results"].get("summary", {})


@app.get("/api/transactions")
def get_transactions(status: Optional[str] = None, db: Session = Depends(get_db), _user: UserDB = Depends(get_current_user)):
    if not _state["last_results"]:
        run_reconciliation(db=db, _user=_user)
    txs = _state["last_results"].get("transactions", [])
    if status:
        txs = [t for t in txs if t.get("status") == status]
    return txs


@app.get("/api/transactions/{tx_id}")
def get_transaction_detail(tx_id: str, db: Session = Depends(get_db), _user: UserDB = Depends(get_current_user)):
    if not _state["last_results"]:
        run_reconciliation(db=db, _user=_user)

    txs = _state["last_results"].get("transactions", [])
    target = next((t for t in txs if t.get("id") == tx_id or t.get("payment_id") == tx_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Transaction not found")

    pay_id = target.get("payment_id", "")
    dfs = _state["last_results"].get("dataframes", {})
    bank_row, ledger_row, settlement_row = {}, {}, {}

    if "bank" in dfs and not dfs["bank"].empty:
        b_match = dfs["bank"][dfs["bank"]["transaction_id"] == target.get("id")]
        if not b_match.empty:
            bank_row = b_match.iloc[0].to_dict()
    if "settlement" in dfs and not dfs["settlement"].empty:
        s_match = dfs["settlement"][dfs["settlement"]["payment_id"] == pay_id]
        if not s_match.empty:
            settlement_row = s_match.iloc[0].to_dict()
    if "ledger" in dfs and not dfs["ledger"].empty:
        l_match = dfs["ledger"][dfs["ledger"]["payment_id"] == pay_id]
        if not l_match.empty:
            ledger_row = l_match.iloc[0].to_dict()

    audit_logger = AuditLogger(db)
    audit_history = audit_logger.get_entries(transaction_id=target.get("id"))

    return {
        "transaction": target,
        "bank_record": bank_row,
        "ledger_record": ledger_row,
        "settlement_record": settlement_row,
        "score_breakdown": target.get("score_breakdown", {}),
        "ai_explanation": target.get("ai_explanation", ""),
        "ai_evidence": target.get("ai_evidence", []),
        "audit_history": audit_history,
    }


@app.get("/api/exceptions")
def get_exceptions(db: Session = Depends(get_db), _user: UserDB = Depends(get_current_user)):
    audit_logger = AuditLogger(db)
    exception_manager = ExceptionManager(db, audit_logger)
    return exception_manager.get_all()


class ExceptionActionRequest(BaseModel):
    reason: Optional[str] = ""


@app.post("/api/exceptions/{exc_id}/approve")
def approve_exception(
    exc_id: str,
    req: Optional[ExceptionActionRequest] = None,
    db: Session = Depends(get_db),
    user: UserDB = Depends(require_min_role("reviewer")),
):
    """Requires reviewer+ role. Reviewer identity comes from the authenticated
    JWT, not a client-supplied field — prevents spoofing who approved a match."""
    audit_logger = AuditLogger(db)
    exception_manager = ExceptionManager(db, audit_logger)
    notes = req.reason if req else "Manually approved."
    try:
        return exception_manager.approve_match(exc_id, reviewer=user.email, notes=notes)
    except KeyError:
        raise HTTPException(status_code=404, detail="Exception ID not found")


@app.post("/api/exceptions/{exc_id}/reject")
def reject_exception(
    exc_id: str,
    req: Optional[ExceptionActionRequest] = None,
    db: Session = Depends(get_db),
    user: UserDB = Depends(require_min_role("reviewer")),
):
    audit_logger = AuditLogger(db)
    exception_manager = ExceptionManager(db, audit_logger)
    reason = req.reason if req else "Manually rejected."
    try:
        return exception_manager.reject_match(exc_id, reviewer=user.email, reason=reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="Exception ID not found")


@app.get("/api/audit")
def get_audit(db: Session = Depends(get_db), _user: UserDB = Depends(get_current_user)):
    audit_logger = AuditLogger(db)
    return audit_logger.get_timeline()


@app.get("/api/evaluation")
def get_evaluation(db: Session = Depends(get_db), _user: UserDB = Depends(get_current_user)):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic"))
    gt_file = os.path.join(base_dir, "ground_truth.json")

    gt_data = []
    if os.path.exists(gt_file):
        with open(gt_file, "r") as f:
            gt_data = json.load(f)

    if not _state["last_results"]:
        run_reconciliation(db=db, _user=_user)

    return eval_engine.evaluate(_state["last_results"], gt_data)


class ChatMessageRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat(req: ChatMessageRequest, db: Session = Depends(get_db), _user: UserDB = Depends(get_current_user)):
    if not _state["last_results"]:
        run_reconciliation(db=db, _user=_user)
    return chat_controller.answer(req.message, _state["last_results"])
