"""
SQLAlchemy DB Models for RazorRecon AI.
"""

import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, JSON, DateTime, Text, UniqueConstraint
from datetime import datetime, timezone

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class UserDB(Base):
    """
    Application users with role-based access control.

    Roles:
      - admin:    full access incl. user management and exception resolution
      - reviewer: can approve/reject exceptions, run reconciliation
      - viewer:   read-only access to dashboard/audit/transactions
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="viewer", nullable=False)  # admin | reviewer | viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())
    last_login_at = Column(String, nullable=True)


class ReconciliationRunDB(Base):
    """
    Persisted snapshot of each reconciliation pipeline run, so results survive
    restarts/redeploys and multiple backend workers see consistent state
    (the old design kept results only in in-process memory).
    """
    __tablename__ = "reconciliation_runs"

    id = Column(String, primary_key=True, default=_uuid)
    triggered_by = Column(String, nullable=True)  # user id or "system"
    source = Column(String, default="csv_upload")  # csv_upload | razorpay_api | demo
    started_at = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())
    completed_at = Column(String, nullable=True)
    summary = Column(JSON, default=dict)
    is_latest = Column(Boolean, default=True, index=True)


class WebhookEventDB(Base):
    """
    Immutable log of received Razorpay webhook events, keyed by Razorpay's
    event id for idempotency (Razorpay may redeliver the same event).
    """
    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("razorpay_event_id", name="uq_webhook_event_id"),)

    id = Column(String, primary_key=True, default=_uuid)
    razorpay_event_id = Column(String, index=True, nullable=True)
    event_type = Column(String, index=True)
    payload = Column(JSON)
    signature_verified = Column(Boolean, default=False)
    processed = Column(Boolean, default=False)
    received_at = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())
    error = Column(Text, nullable=True)


class AuditLogDB(Base):
    __tablename__ = "audit_log"
    
    id = Column(String, primary_key=True)
    timestamp = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())
    transaction_id = Column(String, index=True)
    action = Column(String)
    reason = Column(Text)
    confidence = Column(Float)
    agent = Column(String)
    details = Column(JSON)
    rule_used = Column(String)


class ExceptionDB(Base):
    __tablename__ = "exceptions"
    
    id = Column(String, primary_key=True)
    transaction_id = Column(String, index=True)
    payment_id = Column(String, index=True)
    exception_type = Column(String)
    expected_amount = Column(Float)
    actual_amount = Column(Float)
    difference = Column(Float)
    date_difference_days = Column(Integer)
    details = Column(JSON)
    ai_confidence = Column(Float)
    ai_explanation = Column(Text)
    ai_evidence = Column(JSON)
    recommended_action = Column(String)
    status = Column(String, default="pending")
    created_at = Column(String)
    resolved_at = Column(String, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolution_reason = Column(Text, nullable=True)
