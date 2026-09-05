# --- Stage 1: build dependencies in an isolated layer ---
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 2: slim runtime image ---
FROM python:3.12-slim AS runtime

# libpq5 (not -dev) is the runtime-only Postgres client library.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 razorrecon \
    && useradd --uid 1000 --gid razorrecon --shell /bin/bash --create-home razorrecon

WORKDIR /app

# Bring in pre-built dependencies from the builder stage only — keeps the
# final image free of build toolchains (smaller attack surface + image size).
COPY --from=builder /root/.local /home/razorrecon/.local
ENV PATH=/home/razorrecon/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --chown=razorrecon:razorrecon . .

# Never bake real fixtures/synthetic data assumptions into prod expectations —
# the app itself gates demo-data loading behind APP_ENV != production.
USER razorrecon

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# gunicorn manages multiple uvicorn worker processes — the standard
# production pattern for FastAPI (uvicorn alone is fine for dev, but
# gunicorn adds process supervision, graceful restarts, and worker recycling).
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
