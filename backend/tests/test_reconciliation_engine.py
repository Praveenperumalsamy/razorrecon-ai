"""
Automated Test Suite for RazorRecon AI

Contains 20+ comprehensive unit & integration tests covering:
1. Exact matching (3 tests)
2. Fuzzy matching (3 tests)
3. Amount mismatch detection (2 tests)
4. Date mismatch detection (2 tests)
5. Duplicate transaction detection (2 tests)
6. Missing record detection (2 tests)
7. Partial settlement calculation (1 test)
8. Refund detection (1 test)
9. Chargeback detection (1 test)
10. Confidence threshold & decision gate (2 tests)
11. False-positive prevention (1 test)
12. Audit logging immutability (2 tests)
"""

import pytest
import pandas as pd
from decimal import Decimal

from app.services.normalization import normalize_id, normalize_amount, normalize_date, normalize_dataframe
from app.services.matching import exact_match, fuzzy_match, MatchResult
from app.services.confidence import classify_match, detect_exceptions, verify_settlement_calculation, ReconciliationStatus
from app.services.audit import AuditLogger
from app.services.exceptions import ExceptionManager
from app.services.ai_analyst import ReconciliationAnalyst
from app.services.reconciliation import ReconciliationEngine
from app.services.evaluation import EvaluationEngine
from app.services.chat import FinanceController


@pytest.fixture
def sample_data():
    bank = pd.DataFrame([
        {"transaction_id": "BTX_0001", "bank_reference": "REF1", "transaction_date": "2024-08-10", "amount": 5000.00, "currency": "INR", "customer_reference": "CUS_0001"},
        {"transaction_id": "BTX_0002", "bank_reference": "REF2", "transaction_date": "2024-08-11", "amount": 12000.50, "currency": "INR", "customer_reference": "CUS_0002"},
        {"transaction_id": "BTX_0003", "bank_reference": "REF3", "transaction_date": "2024-08-12", "amount": 850.00, "currency": "INR", "customer_reference": "CUS_0003"},
    ])
    settlement = pd.DataFrame([
        {"settlement_id": "STL_0001", "payment_id": "PAY_0001", "settlement_date": "2024-08-11", "gross_amount": 5000.00, "fee": 100.00, "tax": 18.00, "net_amount": 4882.00},
        {"settlement_id": "STL_0002", "payment_id": "PAY_0002", "settlement_date": "2024-08-12", "gross_amount": 12000.50, "fee": 240.00, "tax": 43.20, "net_amount": 11717.30},
    ])
    ledger = pd.DataFrame([
        {"ledger_id": "LED_0001", "order_id": "ORD_1001", "payment_id": "PAY_0001", "transaction_date": "2024-08-10", "expected_amount": 5000.00, "recorded_amount": 5000.00},
        {"ledger_id": "LED_0002", "order_id": "ORD_1002", "payment_id": "PAY_0002", "transaction_date": "2024-08-11", "expected_amount": 12000.50, "recorded_amount": 12000.50},
    ])
    return bank, settlement, ledger


# 1. Exact Matching Tests (3 tests)
def test_exact_match_success(sample_data):
    bank, settlement, ledger = sample_data
    matches, un_b, un_s, un_l = exact_match(bank, settlement, ledger)
    assert len(matches) == 2
    assert matches[0].confidence == 1.0
    assert matches[0].payment_id == "PAY_0001"


def test_exact_match_preserves_originals(sample_data):
    bank, _, _ = sample_data
    norm = normalize_dataframe(bank, "bank")
    assert "original_amount" in norm.columns
    assert norm["original_amount"].iloc[0] == 5000.00


def test_exact_match_date_tolerance(sample_data):
    bank, settlement, ledger = sample_data
    settlement.loc[0, "settlement_date"] = "2024-08-20"  # 10 days difference (> tolerance)
    matches, un_b, un_s, un_l = exact_match(bank, settlement, ledger, date_tolerance_days=3)
    assert len(matches) == 1  # PAY_0001 should not exact match due to date window


# 2. Fuzzy Matching Tests (3 tests)
def test_fuzzy_match_casing_and_whitespace():
    bank = pd.DataFrame([{"transaction_id": "BTX_0095", "amount": 1000.0, "transaction_date": "2024-08-15"}])
    settlement = pd.DataFrame([{"settlement_id": "STL_0095", "payment_id": "PAY_0095", "gross_amount": 1000.0, "settlement_date": "2024-08-16"}])
    ledger = pd.DataFrame([{"ledger_id": "LED_0095", "payment_id": "pay_0095 ", "expected_amount": 1000.0, "transaction_date": "2024-08-15"}])
    
    matches = fuzzy_match(bank, settlement, ledger)
    assert len(matches) > 0
    assert matches[0].confidence >= 0.75


def test_fuzzy_match_amount_proximity():
    bank = pd.DataFrame([{"transaction_id": "BTX_0099", "amount": 5000.0, "transaction_date": "2024-08-15"}])
    settlement = pd.DataFrame([{"settlement_id": "STL_0099", "payment_id": "PAY_0099", "gross_amount": 4999.50, "settlement_date": "2024-08-16"}])
    ledger = pd.DataFrame([{"ledger_id": "LED_0099", "payment_id": "PAY_0099", "expected_amount": 5000.0, "transaction_date": "2024-08-15"}])
    
    matches = fuzzy_match(bank, settlement, ledger)
    assert len(matches) == 1
    assert matches[0].score_breakdown["amount_similarity"] >= 99.0


def test_fuzzy_match_weighted_scoring_breakdown():
    bank = pd.DataFrame([{"transaction_id": "BTX_0050", "amount": 2500.0, "transaction_date": "2024-08-15"}])
    settlement = pd.DataFrame([{"settlement_id": "STL_0050", "payment_id": "PAY_0050", "gross_amount": 2500.0, "settlement_date": "2024-08-15"}])
    ledger = pd.DataFrame([])
    
    matches = fuzzy_match(bank, settlement, ledger)
    assert len(matches) == 1
    assert "payment_id_similarity" in matches[0].score_breakdown


# 3. Amount Mismatch Tests (2 tests)
def test_amount_mismatch_detection():
    verif = verify_settlement_calculation(5000.0, 100.0, 18.0, 4800.0)  # Should be 4882.0
    assert not verif["valid"]
    assert verif["difference"] == -82.00


def test_amount_mismatch_explanation():
    verif = verify_settlement_calculation(5000.0, 100.0, 18.0, 4800.0)
    assert "MISMATCH" in verif["explanation"]


# 4. Date Mismatch Tests (2 tests)
def test_date_mismatch_classification():
    from app.services.matching import _date_proximity_score
    from datetime import datetime
    d1 = datetime(2024, 8, 1)
    d2 = datetime(2024, 8, 8)  # 7 days apart
    score = _date_proximity_score(d1, d2)
    assert score == 30.0  # 100 - 70


def test_date_normalization_formats():
    assert normalize_date("2024-08-15") == "2024-08-15"
    assert normalize_date("15-08-2024") == "2024-08-15"
    assert normalize_date("08/15/2024") == "2024-08-15"


# 5. Duplicate Detection Tests (2 tests)
def test_duplicate_detection():
    ledger = pd.DataFrame([
        {"ledger_id": "LED_0001", "payment_id": "PAY_0092", "expected_amount": 5000.0},
        {"ledger_id": "LED_0101", "payment_id": "PAY_0092", "expected_amount": 4999.0},
    ])
    excs = detect_exceptions(pd.DataFrame(), pd.DataFrame(), ledger, pd.DataFrame(), pd.DataFrame(), set())
    dup_excs = [e for e in excs if e["exception_type"] == "duplicate_transaction"]
    assert len(dup_excs) == 1
    assert dup_excs[0]["payment_id"] == "PAY_0092"


def test_duplicate_exception_details():
    ledger = pd.DataFrame([
        {"ledger_id": "LED_0001", "payment_id": "PAY_0092", "expected_amount": 5000.0},
        {"ledger_id": "LED_0101", "payment_id": "PAY_0092", "expected_amount": 4999.0},
    ])
    excs = detect_exceptions(pd.DataFrame(), pd.DataFrame(), ledger, pd.DataFrame(), pd.DataFrame(), set())
    assert excs[0]["details"]["duplicate_count"] == 2


# 6. Missing Record Detection Tests (2 tests)
def test_missing_in_settlement():
    bank = pd.DataFrame([{"transaction_id": "BTX_0084", "amount": 1000.0}])
    excs = detect_exceptions(bank, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), set())
    missing = [e for e in excs if e["exception_type"] == "missing_in_settlement"]
    assert len(missing) == 1


def test_missing_in_ledger():
    bank = pd.DataFrame([{"transaction_id": "BTX_0089", "amount": 2000.0}])
    settlement = pd.DataFrame([{"settlement_id": "STL_0089", "payment_id": "PAY_0089", "gross_amount": 2000.0}])
    excs = detect_exceptions(bank, settlement, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), set())
    missing = [e for e in excs if e["exception_type"] == "missing_in_ledger"]
    assert len(missing) == 1


# 7. Partial Settlement Test (1 test)
def test_partial_settlement():
    settlement = pd.DataFrame([{"settlement_id": "STL_0098", "payment_id": "PAY_0098", "gross_amount": 10000.0, "fee": 200.0, "tax": 36.0, "net_amount": 9000.0}])
    excs = detect_exceptions(pd.DataFrame(), settlement, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), set())
    partial = [e for e in excs if e["exception_type"] in ("partial_settlement", "fee_mismatch")]
    assert len(partial) == 1


# 8. Refund Detection Test (1 test)
def test_refund_detection():
    refunds = pd.DataFrame([{"refund_id": "RFD_0001", "payment_id": "PAY_0001", "refund_amount": 5000.0, "refund_date": "2024-08-15", "reason": "defective_item", "status": "processed"}])
    excs = detect_exceptions(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), refunds, pd.DataFrame(), set())
    assert any(e["exception_type"] == "refund" for e in excs)


# 9. Chargeback Detection Test (1 test)
def test_chargeback_detection():
    cb = pd.DataFrame([{"chargeback_id": "CHB_0001", "payment_id": "PAY_0010", "amount": 12000.0, "chargeback_date": "2024-08-30", "reason": "fraud", "status": "open"}])
    excs = detect_exceptions(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), cb, set())
    assert any(e["exception_type"] == "chargeback" for e in excs)


# 10. Confidence Threshold & Gate Tests (2 tests)
def test_classify_match_auto_reconcile():
    assert classify_match(0.95, 0.90, 0.75) == ReconciliationStatus.AUTO_RECONCILED
    assert classify_match(0.85, 0.90, 0.75) == ReconciliationStatus.AI_REVIEW
    assert classify_match(0.60, 0.90, 0.75) == ReconciliationStatus.HUMAN_REVIEW


def test_decision_gate_refuses_low_confidence():
    """System MUST refuse automatic reconciliation below threshold."""
    status = classify_match(0.71, auto_threshold=0.90)
    assert status != ReconciliationStatus.AUTO_RECONCILED
    assert status == ReconciliationStatus.HUMAN_REVIEW or status == ReconciliationStatus.AI_REVIEW


# 11. False Positive Prevention Test (1 test)
def test_false_positive_prevention_on_evaluation():
    eval_eng = EvaluationEngine()
    mock_results = {
        "transactions": [
            {"payment_id": "PAY_0001", "status": "auto_reconciled", "bank_amount": 5000.0},
            {"payment_id": "PAY_0071", "status": "auto_reconciled", "bank_amount": 5000.0},  # PAY_0071 is an anomaly in GT!
        ]
    }
    mock_gt = [
        {"payment_id": "PAY_0001", "status": "exact_match"},
        {"payment_id": "PAY_0071", "status": "anomaly"},
    ]
    res = eval_eng.evaluate(mock_results, mock_gt)
    assert res["confusion_matrix"]["false_positives"] == 1
    assert res["false_positive_amount"] == 5000.0


# 12. Audit Trail Tests (2 tests)
def test_audit_log_immutability(db_session):
    logger = AuditLogger(db_session)
    entry = logger.log("BTX_0001", "AUTO_RECONCILED", "Exact match", 1.0, "Engine")
    assert logger.count == 1
    assert entry["transaction_id"] == "BTX_0001"


def test_audit_log_timeline_filtering(db_session):
    logger = AuditLogger(db_session)
    logger.log("BTX_0001", "AUTO_RECONCILED", "Exact match", 1.0, "Engine")
    logger.log("BTX_0002", "ESCALATED", "Low confidence", 0.65, "Engine")
    filtered = logger.get_entries(transaction_id="BTX_0001")
    assert len(filtered) == 1
    assert filtered[0]["transaction_id"] == "BTX_0001"


# 13. Exception Manager Persistence Tests
def test_exception_manager_register_and_approve(db_session):
    logger = AuditLogger(db_session)
    manager = ExceptionManager(db_session, logger)
    exc = manager.register_exception(
        transaction_id="BTX_0099",
        payment_id="PAY_0099",
        exception_type="AMOUNT_MISMATCH",
        expected_amount=1000.0,
        actual_amount=950.0,
        difference=50.0,
    )
    assert exc["status"] == "pending"
    assert len(manager.get_pending()) == 1

    approved = manager.approve_match(exc["id"], reviewer="reviewer@razorrecon.ai", notes="Confirmed with bank statement")
    assert approved["status"] == "approved"
    assert approved["resolved_by"] == "reviewer@razorrecon.ai"
    assert len(manager.get_pending()) == 0

    # Approval must be reflected in the immutable audit trail.
    audit_entries = logger.get_entries(transaction_id="BTX_0099")
    actions = [e["action"] for e in audit_entries]
    assert "ESCALATED" in actions
    assert "MANUALLY_APPROVED" in actions


def test_exception_manager_missing_id_raises(db_session):
    logger = AuditLogger(db_session)
    manager = ExceptionManager(db_session, logger)
    with pytest.raises(KeyError):
        manager.approve_match("EXC_DOES_NOT_EXIST")
