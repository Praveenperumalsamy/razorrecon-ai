"""
Inbound webhook endpoints.

Razorpay webhooks push near-real-time events (payment.captured,
settlement.processed, refund.processed, payment.dispute.created, etc).
This endpoint verifies the signature, stores the raw event idempotently,
and hands it off for processing — never trusts a webhook body without a
verified signature.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import WebhookEventDB
from app.services.razorpay_client import verify_webhook_signature

logger = logging.getLogger("razorrecon.webhooks")
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/razorpay", status_code=status.HTTP_202_ACCEPTED)
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str = Header(default=""),
):
    raw_body = await request.body()
    signature_ok = verify_webhook_signature(raw_body, x_razorpay_signature)

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_id = request.headers.get("x-razorpay-event-id") or payload.get("id")
    event_type = payload.get("event", "unknown")

    if not signature_ok:
        # Log the attempt (without trusting its contents) but reject it.
        # This is a security event — surface it distinctly in logs/alerts.
        logger.warning("razorpay_webhook_signature_invalid", extra={"event_type": event_type})
        db.add(
            WebhookEventDB(
                razorpay_event_id=event_id,
                event_type=event_type,
                payload=payload,
                signature_verified=False,
                processed=False,
                error="Signature verification failed",
            )
        )
        db.flush()
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Idempotency: Razorpay may redeliver the same event; skip if already seen.
    if event_id:
        existing = db.query(WebhookEventDB).filter(WebhookEventDB.razorpay_event_id == event_id).first()
        if existing:
            return {"status": "already_processed", "event_id": event_id}

    event = WebhookEventDB(
        razorpay_event_id=event_id,
        event_type=event_type,
        payload=payload,
        signature_verified=True,
        processed=False,
    )
    db.add(event)
    db.flush()

    # NOTE: Actual downstream processing (e.g. re-running reconciliation for
    # the affected payment_id, updating settlement records) is intentionally
    # decoupled here — enqueue `event.id` onto a background worker / task
    # queue (Celery, RQ, or FastAPI BackgroundTasks) rather than doing heavy
    # work inline in the webhook handler, so Razorpay's delivery timeout
    # (a few seconds) is never at risk of being exceeded.
    logger.info("razorpay_webhook_received", extra={"event_type": event_type, "event_id": event_id})

    return {"status": "accepted", "event_id": event_id, "event_type": event_type}
