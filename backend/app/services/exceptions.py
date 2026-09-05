"""
Exception Management Service for RazorRecon AI

Manages the unresolved-exception / human-review queue, persisted to the
`exceptions` table. Every resolution (approve/reject) writes an audit entry.
"""

import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .audit import AuditLogger
from app.models.db_models import ExceptionDB


class ExceptionManager:
    """Human-in-the-loop exception manager backed by the database."""

    def __init__(self, db: Session, audit_logger: AuditLogger):
        self.db = db
        self.audit = audit_logger

    def register_exception(
        self,
        transaction_id: str,
        payment_id: str,
        exception_type: str,
        expected_amount: float,
        actual_amount: float,
        difference: float,
        date_difference_days: int = 0,
        details: Optional[dict] = None,
        possible_matches: Optional[list] = None,
        ai_analysis: Optional[dict] = None,
    ) -> Dict[str, Any]:
        ai_conf = ai_analysis.get("confidence", 0.5) if ai_analysis else 0.5
        ai_exp = (
            ai_analysis.get("reason", "Requires human review due to ambiguity.")
            if ai_analysis
            else "Requires human review."
        )
        ai_ev = ai_analysis.get("evidence", []) if ai_analysis else []
        rec_act = ai_analysis.get("recommended_action", "human_review") if ai_analysis else "human_review"

        merged_details = dict(details or {})
        if possible_matches:
            merged_details["possible_matches"] = possible_matches

        # De-dupe: a given transaction/exception_type combo should only ever
        # have ONE exception record. Re-running reconciliation (re-upload,
        # retry, etc.) must not spawn duplicate rows or resurrect exceptions
        # a human has already approved/rejected.
        existing = (
            self.db.query(ExceptionDB)
            .filter(
                ExceptionDB.transaction_id == transaction_id,
                ExceptionDB.exception_type == exception_type,
            )
            .order_by(ExceptionDB.created_at.desc())
            .first()
        )

        if existing is not None:
            if existing.status != "pending":
                # Already resolved by a human — leave their decision intact.
                return self._to_dict(existing)

            # Still pending: refresh it in place with the latest analysis
            # instead of inserting a duplicate row.
            existing.expected_amount = expected_amount
            existing.actual_amount = actual_amount
            existing.difference = difference
            existing.date_difference_days = date_difference_days
            existing.details = merged_details
            existing.ai_confidence = ai_conf
            existing.ai_explanation = ai_exp
            existing.ai_evidence = ai_ev
            existing.recommended_action = rec_act
            self.db.flush()
            return self._to_dict(existing)

        exc = ExceptionDB(
            id=f"EXC_{uuid.uuid4().hex[:10]}",
            transaction_id=transaction_id,
            payment_id=payment_id,
            exception_type=exception_type,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            difference=difference,
            date_difference_days=date_difference_days,
            details=merged_details,
            ai_confidence=ai_conf,
            ai_explanation=ai_exp,
            ai_evidence=ai_ev,
            recommended_action=rec_act,
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.add(exc)
        self.db.flush()

        self.audit.log(
            transaction_id=transaction_id,
            action="ESCALATED",
            reason=f"Exception detected: {exception_type}. Confidence ({ai_conf:.2f}) below auto-reconciliation threshold.",
            confidence=ai_conf,
            agent="ReconciliationEngine",
            details={"exception_id": exc.id, "exception_type": exception_type, "difference": difference},
            rule_used="CONFIDENCE_DECISION_GATE",
        )

        return self._to_dict(exc)

    def approve_match(self, exception_id: str, reviewer: str = "Human Reviewer", notes: str = "") -> Dict[str, Any]:
        exc = self.db.query(ExceptionDB).filter(ExceptionDB.id == exception_id).first()
        if exc is None:
            raise KeyError(f"Exception {exception_id} not found.")

        before_state = self._to_dict(exc)
        exc.status = "approved"
        exc.resolved_at = datetime.now(timezone.utc).isoformat()
        exc.resolved_by = reviewer
        exc.resolution_reason = notes or "Manually approved by human reviewer."
        self.db.flush()
        after_state = self._to_dict(exc)

        self.audit.log(
            transaction_id=exc.transaction_id,
            action="MANUALLY_APPROVED",
            reason=notes or f"Human reviewer {reviewer} approved match for {exc.payment_id}.",
            confidence=1.0,
            agent=reviewer,
            before_state=before_state,
            after_state=after_state,
            rule_used="HUMAN_IN_THE_LOOP_APPROVAL",
        )
        return after_state

    def reject_match(self, exception_id: str, reviewer: str = "Human Reviewer", reason: str = "") -> Dict[str, Any]:
        exc = self.db.query(ExceptionDB).filter(ExceptionDB.id == exception_id).first()
        if exc is None:
            raise KeyError(f"Exception {exception_id} not found.")

        before_state = self._to_dict(exc)
        exc.status = "rejected"
        exc.resolved_at = datetime.now(timezone.utc).isoformat()
        exc.resolved_by = reviewer
        exc.resolution_reason = reason or "Manually rejected by human reviewer."
        self.db.flush()
        after_state = self._to_dict(exc)

        self.audit.log(
            transaction_id=exc.transaction_id,
            action="MANUALLY_REJECTED",
            reason=reason or f"Human reviewer {reviewer} rejected match for {exc.payment_id}.",
            confidence=0.0,
            agent=reviewer,
            before_state=before_state,
            after_state=after_state,
            rule_used="HUMAN_IN_THE_LOOP_REJECTION",
        )
        return after_state

    def get_pending(self) -> List[Dict[str, Any]]:
        return [self._to_dict(e) for e in self.db.query(ExceptionDB).filter(ExceptionDB.status == "pending").all()]

    def get_all(self) -> List[Dict[str, Any]]:
        return [self._to_dict(e) for e in self.db.query(ExceptionDB).all()]

    def get_by_id(self, exception_id: str) -> Optional[Dict[str, Any]]:
        exc = self.db.query(ExceptionDB).filter(ExceptionDB.id == exception_id).first()
        return self._to_dict(exc) if exc else None

    @staticmethod
    def _to_dict(exc: ExceptionDB) -> Dict[str, Any]:
        details = exc.details or {}
        return {
            "id": exc.id,
            "transaction_id": exc.transaction_id,
            "payment_id": exc.payment_id,
            "exception_type": exc.exception_type,
            "expected_amount": exc.expected_amount,
            "actual_amount": exc.actual_amount,
            "difference": exc.difference,
            "date_difference_days": exc.date_difference_days,
            "details": details,
            "possible_matches": details.get("possible_matches", []),
            "ai_confidence": exc.ai_confidence,
            "ai_explanation": exc.ai_explanation,
            "ai_evidence": exc.ai_evidence or [],
            "recommended_action": exc.recommended_action,
            "status": exc.status,
            "created_at": exc.created_at,
            "resolved_at": exc.resolved_at,
            "resolved_by": exc.resolved_by,
            "resolution_reason": exc.resolution_reason,
        }