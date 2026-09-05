"""
Shared pytest fixtures for the RazorRecon AI backend test suite.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("USE_SQLITE", "true")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-production-use-000000")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import db_models  # noqa: F401 — registers all tables on Base.metadata


@pytest.fixture()
def db_session():
    """
    Fresh in-memory SQLite database per test — fast, isolated, no shared state
    between tests (unlike a single module-level engine, which would leak
    audit/exception rows across test cases). StaticPool ensures every
    connection checkout shares the same in-memory DB instead of each one
    getting its own blank database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
