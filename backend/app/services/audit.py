"""
Audit Trail Service for RazorRecon AI

Immutable, DB-persisted audit logging for every reconciliation action.
Every automated and manual decision is permanently recorded in the
`audit_log` table — it survives process restarts and is visible across all
backend workers, which is required for a real compliance/audit trail
(the original in-memory-only version lost history on every redeploy).

Entries are append-only: there is no update/delete method by design.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.models.db_models import AuditLogDB


class AuditLogger:
    """Append-only, DB-backed audit logger bound to a request-scoped DB session."""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        transaction_id: str,
        action: str,
        reason: str,
        confidence: float,
        agent: str = "ReconciliationEngine",
        details: Optional[dict] = None,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        data_sources: Optional[List[str]] = None,
        evidence: Optional[List[str]] = None,
        rule_used: Optional[str] = None,
    ) -> Dict[str, Any]:
        merged_details = dict(details or {})
        if before_state:
            merged_details["before_state"] = before_state
        if after_state:
            merged_details["after_state"] = after_state
        if data_sources:
            merged_details["data_sources"] = data_sources
        if evidence:
            merged_details["evidence"] = evidence

        entry = AuditLogDB(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(timezone.utc).isoformat(),
            transaction_id=transaction_id,
            action=action,
            reason=reason,
            confidence=confidence,
            agent=agent,
            details=merged_details,
            rule_used=rule_used or "",
        )
        self.db.add(entry)
        self.db.flush()
        return self._to_dict(entry)

    def get_entries(self, transaction_id: Optional[str] = None) -> List[Dict[str, Any]]:
        q = self.db.query(AuditLogDB)
        if transaction_id:
            q = q.filter(AuditLogDB.transaction_id == transaction_id)
        return [self._to_dict(e) for e in q.order_by(AuditLogDB.timestamp.asc()).all()]

    def get_timeline(self) -> List[Dict[str, Any]]:
        entries = self.db.query(AuditLogDB).order_by(AuditLogDB.timestamp.asc()).all()
        return [self._to_dict(e) for e in entries]

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        entries = (
            self.db.query(AuditLogDB).order_by(AuditLogDB.timestamp.desc()).limit(limit).all()
        )
        return [self._to_dict(e) for e in entries]

    @property
    def count(self) -> int:
        return self.db.query(AuditLogDB).count()

    @staticmethod
    def _to_dict(entry: AuditLogDB) -> Dict[str, Any]:
        return {
            "id": entry.id,
            "timestamp": entry.timestamp,
            "transaction_id": entry.transaction_id,
            "action": entry.action,
            "reason": entry.reason,
            "confidence": entry.confidence,
            "agent": entry.agent,
            "details": entry.details or {},
            "rule_used": entry.rule_used,
        }
