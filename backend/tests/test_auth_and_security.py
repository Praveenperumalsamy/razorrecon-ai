"""
API-level tests for authentication, RBAC enforcement, and core security
behaviors (as opposed to test_reconciliation_engine.py, which tests the
matching/scoring logic directly).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    """Spins up the full FastAPI app against an isolated in-memory DB per test.

    Uses StaticPool so every connection checkout shares the same underlying
    in-memory SQLite database — without it, each new session would get its
    own blank ":memory:" database and every table-lookup would 404.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
            db.commit()
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Rate limiting uses a process-wide in-memory store keyed by client IP;
    # since TestClient always looks like the same "testclient" address,
    # reset it between tests so one test's requests don't trip another's
    # rate limit.
    app.state.limiter.reset()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def _register_and_login(client, email="user@razorrecon.ai", password="SuperSecret123!"):
    client.post("/api/auth/register", json={"email": email, "password": password})
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    return resp.json()["access_token"], resp.json()["role"]


def test_first_registered_user_becomes_admin(client):
    token, role = _register_and_login(client, "first@razorrecon.ai")
    assert role == "admin"


def test_second_registered_user_is_viewer_by_default(client):
    _register_and_login(client, "first@razorrecon.ai")
    token, role = _register_and_login(client, "second@razorrecon.ai")
    assert role == "viewer"


def test_login_rejects_wrong_password(client):
    client.post("/api/auth/register", json={"email": "u@razorrecon.ai", "password": "SuperSecret123!"})
    resp = client.post("/api/auth/login", data={"username": "u@razorrecon.ai", "password": "WrongPassword123!"})
    assert resp.status_code == 401


def test_protected_endpoint_requires_auth(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 401


def test_viewer_cannot_trigger_reconciliation(client):
    """Viewer role must NOT be able to trigger a reconciliation run (reviewer+ only)."""
    _register_and_login(client, "first@razorrecon.ai")  # admin bootstrap
    token, role = _register_and_login(client, "viewer@razorrecon.ai")
    assert role == "viewer"
    resp = client.post("/api/reconcile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_can_trigger_reconciliation(client):
    token, role = _register_and_login(client, "admin@razorrecon.ai")
    assert role == "admin"
    resp = client.post("/api/reconcile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "summary" in resp.json()


def test_admin_can_promote_user_role(client):
    admin_token, _ = _register_and_login(client, "admin@razorrecon.ai")
    viewer_token, _ = _register_and_login(client, "viewer2@razorrecon.ai")

    users = client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_token}"}).json()
    viewer_user = next(u for u in users if u["email"] == "viewer2@razorrecon.ai")

    resp = client.post(
        f"/api/auth/users/{viewer_user['id']}/role",
        json={"role": "reviewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "reviewer"


def test_non_admin_cannot_list_users(client):
    _register_and_login(client, "admin@razorrecon.ai")
    viewer_token, _ = _register_and_login(client, "viewer3@razorrecon.ai")
    resp = client.get("/api/auth/users", headers={"Authorization": f"Bearer {viewer_token}"})
    assert resp.status_code == 403


def test_invalid_token_rejected(client):
    resp = client.get("/api/dashboard", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_webhook_rejects_unverified_signature(client):
    resp = client.post(
        "/api/webhooks/razorpay",
        json={"event": "payment.captured", "id": "evt_test_1"},
        headers={"X-Razorpay-Signature": "invalid"},
    )
    assert resp.status_code == 401


def test_security_headers_present(client):
    resp = client.get("/health/live")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "X-Request-ID" in resp.headers


def test_health_endpoints_do_not_require_auth(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
