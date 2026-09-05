"""
Database connection setup for RazorRecon AI.

Production: PostgreSQL with connection pooling.
Local dev / CI: SQLite fallback (USE_SQLITE=true).

Sessions are request-scoped via the `get_db` dependency — never share a
session across requests or background tasks.
"""

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs = {"echo": False, "future": True}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Real production pooling — SQLite doesn't support pool_size/max_overflow.
    _engine_kwargs.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,  # avoids stale-connection errors after DB restarts
    )

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a request-scoped DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def session_scope():
    """Context manager for DB sessions outside of request handlers (jobs, scripts)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Create all tables. In production this is a safety net only —
    Alembic migrations (see /backend/alembic) are the source of truth."""
    Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """Used by the /health/ready endpoint to verify DB reachability."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
