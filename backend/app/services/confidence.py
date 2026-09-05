"""
Confidence Scoring & Exception Detection for RazorRecon AI

Classification thresholds and deterministic exception detection.
All financial calculations are deterministic — no LLM involvement.
"""

from enum import Enum
from typing import List, Dict, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import numpy as np

from .normalization import normalize_id, create_payment_id_mapping


class ReconciliationStatus(str, Enum):
    AUTO_RECONCILED = "auto_reconciled"
    AI_REVIEW = "ai_review"
    HUMAN_REVIEW = "human_review"
    MANUALLY_APPROVED = "manually_approved"
    MANUALLY_REJECTED = "manually_rejected"
    EXCEPTION = "exception"


class ExceptionType(str, Enum):
    MISSING_IN_BANK = "missing_in_bank"
    MISSING_IN_LEDGER = "missing_in_ledger"
    MISSING_IN_SETTLEMENT = "missing_in_settlement"
    AMOUNT_MISMATCH = "amount_mismatch"
    DATE_MISMATCH = "date_mismatch"
    DUPLICATE_TRANSACTION = "duplicate_transaction"
    PARTIAL_SETTLEMENT = "partial_settlement"
    REFUND = "refund"
    CHARGEBACK = "chargeback"
    FEE_MISMATCH = "fee_mismatch"
    UNKNOWN_EXCEPTION = "unknown_exception"


def classify_match(confidence: float, auto_threshold: float = 0.90,
                   review_threshold: float = 0.75) -> ReconciliationStatus:
    """
    Classify a match based on confidence score.
    
    >= auto_threshold: AUTO_RECONCILED (safe for automatic processing)
    >= review_threshold: AI_REVIEW (AI can assist but needs verification)
    < review_threshold: HUMAN_REVIEW (must be manually reviewed)
    
    This is a critical safety gate. We NEVER auto-reconcile below threshold.
    """
    if confidence >= auto_threshold:
        return ReconciliationStatus.AUTO_RECONCILED
    elif confidence >= review_threshold:
        return ReconciliationStatus.AI_REVIEW
    else:
        return ReconciliationStatus.HUMAN_REVIEW


def verify_settlement_calculation(gross_amount: float, fee: float,
                                   tax: float, net_amount: float) -> dict:
    """
    Deterministic verification: gross - fee - tax should equal net.
    
    This is a CRITICAL financial calculation that must NEVER be delegated to an LLM.
    Uses Decimal for precision.
    
    Returns:
        {
            'valid': bool,
            'expected_net': float,
            'actual_net': float,
            'difference': float,
            'explanation': str
        }
    """
    d_gross = Decimal(str(gross_amount))
    d_fee = Decimal(str(fee))
    d_tax = Decimal(str(tax))
    d_net = Decimal(str(net_amount))
    
    expected_net = (d_gross - d_fee - d_tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    difference = (d_net - expected_net).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    is_valid = abs(difference) < Decimal("0.02")  # Allow 1 paisa rounding
    
    explanation = ""
    if is_valid:
        explanation = (
            f"Settlement verified: ₹{gross_amount:,.2f} - ₹{fee:,.2f} (fee) - "
            f"₹{tax:,.2f} (tax) = ₹{float(expected_net):,.2f} net. "
            f"The ₹{float(d_fee + d_tax):,.2f} difference between gross payment and "
            f"settlement is fully explained by the recorded fee and tax."
        )
    else:
        explanation = (
            f"Settlement MISMATCH: Expected net = ₹{float(expected_net):,.2f} "
            f"(₹{gross_amount:,.2f} - ₹{fee:,.2f} - ₹{tax:,.2f}), "
            f"but actual net = ₹{net_amount:,.2f}. "
            f"Unexplained difference: ₹{abs(float(difference)):,.2f}"
        )
    
    return {
        "valid": is_valid,
        "expected_net": float(expected_net),
        "actual_net": net_amount,
        "difference": float(difference),
        "gross_amount": gross_amount,
        "fee": fee,
        "tax": tax,
        "explanation": explanation,
    }


def detect_exceptions(
    bank_df: pd.DataFrame,
    settlement_df: pd.DataFrame,
    ledger_df: pd.DataFrame,
    refund_df: pd.DataFrame,
    chargeback_df: pd.DataFrame,
    matched_payment_ids: set,
) -> List[Dict[str, Any]]:
    """
    Detect all exception types across datasets.
    
    Scans for:
    1. Missing records (present in one source but not others)
    2. Duplicates (same payment_id appears multiple times)
    3. Refunds and chargebacks
    4. Amount/date mismatches in matched records
    5. Fee mismatches in settlements
    
    Returns list of exception dicts.
    """
    exceptions = []
    exception_counter = 0
    
    # Build payment ID sets from each source
    pay_id_map = create_payment_id_mapping(bank_df)
    bank_pay_ids = set(pay_id_map.values())
    
    settlement_pay_ids = set()
    if not settlement_df.empty and "payment_id" in settlement_df.columns:
        settlement_pay_ids = set(settlement_df["payment_id"].apply(str).values)
    
    ledger_pay_ids = set()
    if not ledger_df.empty and "payment_id" in ledger_df.columns:
        ledger_pay_ids = set(ledger_df["payment_id"].apply(str).values)
    
    # 1. MISSING IN SETTLEMENT — present in bank but not settlement
    missing_in_settlement = bank_pay_ids - settlement_pay_ids - matched_payment_ids
    for pay_id in missing_in_settlement:
        exception_counter += 1
        # Find bank record for this payment
        bank_row = None
        for _, row in bank_df.iterrows():
            if pay_id_map.get(str(row.get("transaction_id", ""))) == pay_id:
                bank_row = row
                break
        
        exceptions.append({
            "id": f"EXC_{str(exception_counter).zfill(4)}",
            "transaction_id": str(bank_row.get("transaction_id", "")) if bank_row is not None else pay_id,
            "payment_id": pay_id,
            "exception_type": ExceptionType.MISSING_IN_SETTLEMENT.value,
            "expected_amount": float(bank_row.get("amount", 0)) if bank_row is not None else 0,
            "actual_amount": 0,
            "difference": float(bank_row.get("amount", 0)) if bank_row is not None else 0,
            "date_difference_days": 0,
            "details": {
                "source": "bank",
                "missing_in": "settlement",
                "bank_record": bank_row.to_dict() if bank_row is not None else {},
            },
            "status": "pending",
            "possible_matches": [],
        })
    
    # 2. MISSING IN LEDGER — present in bank+settlement but not ledger
    missing_in_ledger = (bank_pay_ids & settlement_pay_ids) - ledger_pay_ids - matched_payment_ids
    for pay_id in missing_in_ledger:
        exception_counter += 1
        bank_row = None
        for _, row in bank_df.iterrows():
            if pay_id_map.get(str(row.get("transaction_id", ""))) == pay_id:
                bank_row = row
                break
        
        exceptions.append({
            "id": f"EXC_{str(exception_counter).zfill(4)}",
            "transaction_id": str(bank_row.get("transaction_id", "")) if bank_row is not None else pay_id,
            "payment_id": pay_id,
            "exception_type": ExceptionType.MISSING_IN_LEDGER.value,
            "expected_amount": float(bank_row.get("amount", 0)) if bank_row is not None else 0,
            "actual_amount": 0,
            "difference": float(bank_row.get("amount", 0)) if bank_row is not None else 0,
            "date_difference_days": 0,
            "details": {
                "source": "bank",
                "missing_in": "ledger",
            },
            "status": "pending",
            "possible_matches": [],
        })
    
    # 3. DUPLICATE TRANSACTIONS in ledger
    if not ledger_df.empty and "payment_id" in ledger_df.columns:
        dup_mask = ledger_df.duplicated(subset=["payment_id"], keep=False)
        dup_pay_ids = set(ledger_df[dup_mask]["payment_id"].values)
        for pay_id in dup_pay_ids:
            exception_counter += 1
            dup_rows = ledger_df[ledger_df["payment_id"] == pay_id]
            amounts = dup_rows["expected_amount"].tolist() if "expected_amount" in dup_rows.columns else []
            
            exceptions.append({
                "id": f"EXC_{str(exception_counter).zfill(4)}",
                "transaction_id": str(dup_rows.iloc[0].get("ledger_id", "")),
                "payment_id": str(pay_id),
                "exception_type": ExceptionType.DUPLICATE_TRANSACTION.value,
                "expected_amount": float(amounts[0]) if amounts else 0,
                "actual_amount": float(amounts[1]) if len(amounts) > 1 else 0,
                "difference": abs(float(amounts[0]) - float(amounts[1])) if len(amounts) > 1 else 0,
                "date_difference_days": 0,
                "details": {
                    "duplicate_count": len(dup_rows),
                    "amounts": [float(a) for a in amounts],
                    "ledger_ids": dup_rows["ledger_id"].tolist() if "ledger_id" in dup_rows.columns else [],
                },
                "status": "pending",
                "possible_matches": [],
            })
    
    # 4. REFUNDS
    if not refund_df.empty:
        for _, ref_row in refund_df.iterrows():
            exception_counter += 1
            pay_id = str(ref_row.get("payment_id", ""))
            exceptions.append({
                "id": f"EXC_{str(exception_counter).zfill(4)}",
                "transaction_id": str(ref_row.get("refund_id", "")),
                "payment_id": pay_id,
                "exception_type": ExceptionType.REFUND.value,
                "expected_amount": 0,
                "actual_amount": float(ref_row.get("refund_amount", 0)),
                "difference": float(ref_row.get("refund_amount", 0)),
                "date_difference_days": 0,
                "details": {
                    "refund_id": str(ref_row.get("refund_id", "")),
                    "refund_date": str(ref_row.get("refund_date", "")),
                    "reason": str(ref_row.get("reason", "")),
                    "status": str(ref_row.get("status", "")),
                },
                "status": "pending",
                "possible_matches": [],
            })
    
    # 5. CHARGEBACKS
    if not chargeback_df.empty:
        for _, cb_row in chargeback_df.iterrows():
            exception_counter += 1
            pay_id = str(cb_row.get("payment_id", ""))
            exceptions.append({
                "id": f"EXC_{str(exception_counter).zfill(4)}",
                "transaction_id": str(cb_row.get("chargeback_id", "")),
                "payment_id": pay_id,
                "exception_type": ExceptionType.CHARGEBACK.value,
                "expected_amount": 0,
                "actual_amount": float(cb_row.get("amount", 0)),
                "difference": float(cb_row.get("amount", 0)),
                "date_difference_days": 0,
                "details": {
                    "chargeback_id": str(cb_row.get("chargeback_id", "")),
                    "chargeback_date": str(cb_row.get("chargeback_date", "")),
                    "reason": str(cb_row.get("reason", "")),
                    "status": str(cb_row.get("status", "")),
                },
                "status": "pending",
                "possible_matches": [],
            })
    
    # 6. FEE MISMATCHES in settlements
    if not settlement_df.empty:
        for _, s_row in settlement_df.iterrows():
            gross = float(s_row.get("gross_amount", 0))
            fee = float(s_row.get("fee", 0))
            tax = float(s_row.get("tax", 0))
            net = float(s_row.get("net_amount", 0))
            
            verification = verify_settlement_calculation(gross, fee, tax, net)
            if not verification["valid"]:
                exception_counter += 1
                pay_id = str(s_row.get("payment_id", ""))
                
                # Determine if partial settlement or fee mismatch
                expected_fee_pct = (fee / gross * 100) if gross > 0 else 0
                is_partial = abs(verification["difference"]) > 5  # More than ₹5 off
                
                exc_type = ExceptionType.PARTIAL_SETTLEMENT if is_partial else ExceptionType.FEE_MISMATCH
                
                exceptions.append({
                    "id": f"EXC_{str(exception_counter).zfill(4)}",
                    "transaction_id": str(s_row.get("settlement_id", "")),
                    "payment_id": pay_id,
                    "exception_type": exc_type.value,
                    "expected_amount": verification["expected_net"],
                    "actual_amount": net,
                    "difference": abs(verification["difference"]),
                    "date_difference_days": 0,
                    "details": {
                        "verification": verification,
                        "fee_percentage": round(expected_fee_pct, 2),
                    },
                    "status": "pending",
                    "possible_matches": [],
                })
    
    return exceptions
