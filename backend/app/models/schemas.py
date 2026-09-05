"""
Pydantic Schemas for RazorRecon AI API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class TransactionItem(BaseModel):
    id: str
    payment_id: str
    bank_amount: float
    ledger_amount: float
    settlement_amount: float
    status: str
    confidence: float
    match_type: str
    exception_type: Optional[str] = None
    ai_explanation: Optional[str] = None
    ai_evidence: Optional[List[str]] = None
    reasons: Optional[List[str]] = None
    score_breakdown: Optional[Dict[str, float]] = None
    amount_difference: Optional[float] = 0.0
    date_difference_days: Optional[int] = 0
    date: Optional[str] = ""
    currency: Optional[str] = "INR"


class ExceptionResponse(BaseModel):
    id: str
    transaction_id: str
    payment_id: str
    exception_type: str
    expected_amount: float
    actual_amount: float
    difference: float
    date_difference_days: int
    details: Dict[str, Any]
    possible_matches: List[Dict[str, Any]]
    ai_confidence: float
    ai_explanation: str
    ai_evidence: List[str]
    recommended_action: str
    status: str


class AuditEntryResponse(BaseModel):
    id: str
    timestamp: str
    transaction_id: str
    action: str
    reason: str
    confidence: float
    agent: str
    details: Optional[Dict[str, Any]] = None
    rule_used: Optional[str] = None


class DashboardResponse(BaseModel):
    total_records: int
    reconciled: int
    auto_reconciled: int
    ai_assisted: int
    human_review: int
    exceptions: int
    match_rate: float
    auto_reconciliation_rate: float
    exception_rate: float
    total_amount: float
    reconciled_amount: float
    currency: str


class ChatRequest(BaseModel):
    message: str


class ActionRequest(BaseModel):
    reason: Optional[str] = ""
    reviewer: Optional[str] = "Human Reviewer"
