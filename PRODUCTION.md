# Production Readiness — RazorRecon AI

This document tracks what was hardened for production fintech use, how to
deploy it, and what remains organization-specific (things no amount of code
can decide for you — real credentials, compliance sign-off, infra topology).

## What changed from the hackathon build

| Area | Before | After |
|---|---|---|
| Auth | None — every endpoint open | JWT auth + RBAC (`admin` / `reviewer` / `viewer`) on every data endpoint |
| Audit trail | In-memory Python dict, lost on restart | Persisted to `audit_log` table; append-only, survives restarts, visible across all workers |
| Exception queue | In-memory, lost on restart | Persisted to `exceptions` table |
| Data source | Synthetic CSV fixtures only | CSV upload retained + real Razorpay Settlements/Payments API client + verified webhook ingestion |
| Database | SQLite, no migrations | PostgreSQL with pooled connections; Alembic migrations as source of truth |
| CORS | Wildcard-friendly | Restricted to explicit configured origins; wildcard rejected at startup in prod |
| Secrets | Hardcoded fallback API behavior | Pydantic-validated settings; app **refuses to boot** in production with a weak/missing `SECRET_KEY`, `DEBUG=true`, wildcard CORS, or SQLite |
| Password hashing | N/A (no auth existed) | bcrypt via direct library call (not passlib, which has a known bcrypt 4.x incompatibility) |
| Rate limiting | None | slowapi; stricter limits on `/auth/login` and `/auth/register` |
| Logging | `print()` statements | Structured JSON logs with request-ID correlation; never logs secrets or full bodies |
| Errors | Stack traces could leak to clients | Global handler returns a generic message; full trace goes to logs only |
| Containers | No Dockerfiles existed | Multi-stage, non-root Dockerfiles for backend (gunicorn+uvicorn workers) and frontend (nginx) |
| CI | None | GitHub Actions: backend tests, frontend typecheck/build, Docker build verification |
| Tests | 22 unit tests on matching logic | +14 tests: DB-backed audit/exception persistence, auth flows, RBAC enforcement, security headers |

## Deploying

### Local dev (unchanged workflow, now with Postgres)
```bash
cp .env.example .env        # fill in SECRET_KEY at minimum (openssl rand -hex 32)
docker compose up --build
```

### Production
```bash
cp .env.example .env        # fill in every required value — see below
docker compose -f docker-compose.prod.yml up --build -d
```
`docker-compose.prod.yml` will refuse to start the `backend` and `db`
services if `SECRET_KEY`, `CORS_ORIGINS`, or `POSTGRES_PASSWORD` are unset —
this is intentional (`?VAR must be set` syntax fails fast rather than
silently running insecurely).

Database migrations run automatically via the `migrate` one-shot service
before `backend` starts. To run them manually:
```bash
docker compose -f docker-compose.prod.yml run --rm migrate
```

### First admin account
The **first** user registered via `POST /api/auth/register` on a fresh
database is automatically granted the `admin` role. Register that account
immediately after first deploy, before exposing the app publicly, then
promote/manage other users via `/api/auth/users/{id}/role` (admin only).

## What's still organization-specific

These require real credentials, business decisions, or infra you have that
we don't — code alone can't finish them:

1. **Real Razorpay credentials.** Set `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`
   / `RAZORPAY_WEBHOOK_SECRET` from your live Razorpay Dashboard. Until set,
   the app runs in CSV-upload-only mode (`RazorpayNotConfiguredError` is
   caught, not fatal).
2. **Bank statement ingestion.** Most banks don't expose a public
   reconciliation API — this typically means SFTP pickup of a daily MT940/
   BAI2/CSV file, or a bank-specific API integration. The CSV upload path
   (`/api/upload`) is the integration point; wire your bank's actual delivery
   mechanism (SFTP poller, email attachment parser, etc.) to call it.
3. **Secrets management.** `.env` is fine for local dev. In production, put
   `SECRET_KEY`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`,
   `POSTGRES_PASSWORD`, and `GEMINI_API_KEY` in a real secrets manager (AWS
   Secrets Manager, GCP Secret Manager, Vault, or your orchestrator's native
   secrets) and inject them as environment variables at deploy time — never
   commit them.
4. **PCI-DSS / compliance program.** This app never stores card numbers or
   CVVs (Razorpay/your PSP tokenizes those), which keeps PCI scope small, but
   a real compliance program (SOC 2, ISO 27001, PCI-DSS SAQ) is an
   organizational process, not a code change — this repo doesn't attempt one.
5. **TLS termination.** Not handled in this repo. Terminate TLS at your load
   balancer / ingress / reverse proxy (ALB, nginx-ingress, Cloudflare, etc.)
   in front of the frontend container.
6. **Multi-worker cache consistency.** `_state` in `backend/app/main.py`
   (uploaded dataframes + last computed reconciliation result) is
   process-local. Running more than one gunicorn worker or replica means
   each has its own cache; the durable, cross-worker source of truth is the
   DB-persisted `audit_log` and `exceptions` tables. For true multi-worker
   cache consistency, back `_state` with Redis or object storage — not
   implemented here since it's a real architectural decision (what TTL, what
   eviction policy, whether to move to a job queue) rather than a drop-in fix.
7. **Webhook event processing.** `/api/webhooks/razorpay` verifies the
   signature and stores the event idempotently, but does not yet trigger
   downstream reconciliation re-runs — that's marked with a `NOTE` in
   `backend/app/routers/webhooks.py`. Wire it to a background task queue
   (Celery, RQ, or FastAPI `BackgroundTasks` for light loads) rather than
   processing inline, since Razorpay expects a fast webhook response.
8. **Frontend token storage.** Access/refresh tokens are stored in
   `localStorage` (see comment in `frontend/src/services/api.ts`). This is a
   pragmatic default; for stricter XSS resistance, move to httpOnly, Secure,
   SameSite=strict cookies issued by the backend on login — that needs a
   small backend change (set-cookie) not included in this pass.
9. **Sentry / APM.** `SENTRY_DSN` is wired but optional — set it to enable
   error tracking, or replace with your APM of choice.
10. **Load/perf testing at your real data volume.** The matching engine was
    validated against the bundled 100-record synthetic dataset. Before going
    live, load-test with realistic transaction volumes to confirm the
    fuzzy-matching path (which does a text-similarity scan) scales
    acceptably, and consider indexing/batching for very large daily volumes.

## Running the test suite

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```
36 tests: 22 on matching/scoring logic (unchanged from the original build),
2 on audit trail persistence, 2 on exception manager persistence, and 10 on
auth/RBAC/security headers via FastAPI's `TestClient`.
