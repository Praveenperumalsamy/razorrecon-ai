"""
Matching Service for RazorRecon AI

Implements deterministic exact matching and weighted fuzzy matching.
All financial comparisons use deterministic arithmetic — never LLM.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal

try:
    from thefuzz import fuzz
except ImportError:
    # Fallback: simple ratio
    class _FuzzFallback:
        @staticmethod
        def ratio(a, b):
            if a == b:
                return 100
            return int(max(0, 100 - abs(len(a) - len(b)) * 10))
    fuzz = _FuzzFallback()

from .normalization import normalize_id, create_payment_id_mapping


@dataclass
class MatchResult:
    """Result of a matching operation between two records."""
    source_id: str
    target_id: str
    source_type: str
    target_type: str
    payment_id: str
    confidence: float
    match_type: str  # 'exact', 'fuzzy', 'unmatched'
    reasons: List[str] = field(default_factory=list)
    score_breakdown: dict = field(default_factory=dict)
    amount_difference: float = 0.0
    date_difference_days: int = 0
    bank_amount: float = 0.0
    ledger_amount: float = 0.0
    settlement_amount: float = 0.0
    settlement_net: float = 0.0
    fee: float = 0.0
    tax: float = 0.0

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "payment_id": self.payment_id,
            "confidence": self.confidence,
            "match_type": self.match_type,
            "reasons": self.reasons,
            "score_breakdown": self.score_breakdown,
            "amount_difference": self.amount_difference,
            "date_difference_days": self.date_difference_days,
            "bank_amount": self.bank_amount,
            "ledger_amount": self.ledger_amount,
            "settlement_amount": self.settlement_amount,
            "settlement_net": self.settlement_net,
            "fee": self.fee,
            "tax": self.tax,
        }


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse a normalized date string."""
    if not date_str or pd.isna(date_str):
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
    except ValueError:
        try:
            return pd.to_datetime(date_str).to_pydatetime()
        except Exception:
            return None


def _amount_similarity(a: float, b: float) -> float:
    """Calculate amount similarity score (0-100). Deterministic."""
    if a == 0 and b == 0:
        return 100.0
    if a == b:
        return 100.0
    max_val = max(abs(a), abs(b))
    if max_val == 0:
        return 100.0
    diff_ratio = abs(a - b) / max_val
    return max(0.0, round((1.0 - diff_ratio) * 100, 2))


def _date_proximity_score(date1: Optional[datetime], date2: Optional[datetime]) -> float:
    """Calculate date proximity score (0-100). 0 days=100, 10+ days=0."""
    if date1 is None or date2 is None:
        return 0.0
    days_apart = abs((date1 - date2).days)
    return max(0.0, 100.0 - (days_apart * 10.0))


def _date_diff_days(date1: Optional[datetime], date2: Optional[datetime]) -> int:
    """Calculate absolute day difference between two dates."""
    if date1 is None or date2 is None:
        return 999
    return abs((date1 - date2).days)


def exact_match(
    bank_df: pd.DataFrame,
    settlement_df: pd.DataFrame,
    ledger_df: pd.DataFrame,
    date_tolerance_days: int = 3,
) -> Tuple[List[MatchResult], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Perform deterministic exact matching.
    
    Match criteria:
    - Payment ID exact match (bank BTX→PAY mapping matched to settlement/ledger payment_id)
    - Amount exact match (bank amount == settlement gross_amount == ledger expected_amount)
    - Date within tolerance window
    
    Returns: (matches, unmatched_bank, unmatched_settlement, unmatched_ledger)
    """
    matches = []
    matched_bank_idx = set()
    matched_settlement_idx = set()
    matched_ledger_idx = set()
    
    # Create bank → payment_id mapping
    pay_id_map = create_payment_id_mapping(bank_df)
    
    for b_idx, bank_row in bank_df.iterrows():
        bank_tx_id = str(bank_row.get("transaction_id", ""))
        bank_pay_id = pay_id_map.get(bank_tx_id, "")
        bank_amount = float(bank_row.get("amount", 0))
        bank_date = _parse_date(str(bank_row.get("transaction_date", "")))
        
        if not bank_pay_id:
            continue
        
        # Find matching settlement
        stl_match_idx = None
        stl_row = None
        for s_idx, s_row in settlement_df.iterrows():
            if s_idx in matched_settlement_idx:
                continue
            s_pay_id = str(s_row.get("payment_id", ""))
            if s_pay_id == bank_pay_id:
                s_amount = float(s_row.get("gross_amount", 0))
                s_date = _parse_date(str(s_row.get("settlement_date", "")))
                
                # Amount must match exactly
                if abs(bank_amount - s_amount) < 0.01:
                    # Date must be within tolerance
                    if bank_date and s_date:
                        if abs((bank_date - s_date).days) <= date_tolerance_days:
                            stl_match_idx = s_idx
                            stl_row = s_row
                            break
                    else:
                        stl_match_idx = s_idx
                        stl_row = s_row
                        break
        
        # Find matching ledger
        led_match_idx = None
        led_row = None
        for l_idx, l_row in ledger_df.iterrows():
            if l_idx in matched_ledger_idx:
                continue
            l_pay_id = str(l_row.get("payment_id", ""))
            if l_pay_id == bank_pay_id:
                l_amount = float(l_row.get("expected_amount", 0))
                l_date = _parse_date(str(l_row.get("transaction_date", "")))
                
                if abs(bank_amount - l_amount) < 0.01:
                    if bank_date and l_date:
                        if abs((bank_date - l_date).days) <= date_tolerance_days:
                            led_match_idx = l_idx
                            led_row = l_row
                            break
                    else:
                        led_match_idx = l_idx
                        led_row = l_row
                        break
        
        # If we found matches in both settlement and ledger (or at least settlement)
        if stl_match_idx is not None and led_match_idx is not None:
            stl_date = _parse_date(str(stl_row.get("settlement_date", "")))
            date_diff = _date_diff_days(bank_date, stl_date)
            
            reasons = [
                f"Payment ID exact match: {bank_pay_id}",
                f"Amount exact match: {bank_amount}",
                f"Date within {date_diff} day(s) tolerance",
                "Three-way match: Bank ↔ Settlement ↔ Ledger",
            ]
            
            match = MatchResult(
                source_id=bank_tx_id,
                target_id=str(stl_row.get("settlement_id", "")),
                source_type="bank",
                target_type="settlement",
                payment_id=bank_pay_id,
                confidence=1.0,
                match_type="exact",
                reasons=reasons,
                score_breakdown={
                    "payment_id_similarity": 100,
                    "amount_similarity": 100,
                    "date_proximity": round(100 - date_diff * 10, 1),
                    "customer_reference": 100,
                    "metadata": 100,
                },
                amount_difference=0.0,
                date_difference_days=date_diff,
                bank_amount=bank_amount,
                ledger_amount=float(led_row.get("expected_amount", 0)),
                settlement_amount=float(stl_row.get("gross_amount", 0)),
                settlement_net=float(stl_row.get("net_amount", 0)),
                fee=float(stl_row.get("fee", 0)),
                tax=float(stl_row.get("tax", 0)),
            )
            matches.append(match)
            matched_bank_idx.add(b_idx)
            matched_settlement_idx.add(stl_match_idx)
            matched_ledger_idx.add(led_match_idx)
        
        elif stl_match_idx is not None:
            # Bank + Settlement match only (no ledger)
            stl_date = _parse_date(str(stl_row.get("settlement_date", "")))
            date_diff = _date_diff_days(bank_date, stl_date)
            
            match = MatchResult(
                source_id=bank_tx_id,
                target_id=str(stl_row.get("settlement_id", "")),
                source_type="bank",
                target_type="settlement",
                payment_id=bank_pay_id,
                confidence=0.85,
                match_type="exact",
                reasons=[
                    f"Payment ID exact match: {bank_pay_id}",
                    f"Amount exact match: {bank_amount}",
                    "Two-way match: Bank ↔ Settlement (missing in ledger)",
                ],
                score_breakdown={
                    "payment_id_similarity": 100,
                    "amount_similarity": 100,
                    "date_proximity": round(100 - date_diff * 10, 1),
                    "customer_reference": 50,
                    "metadata": 50,
                },
                amount_difference=0.0,
                date_difference_days=date_diff,
                bank_amount=bank_amount,
                settlement_amount=float(stl_row.get("gross_amount", 0)),
                settlement_net=float(stl_row.get("net_amount", 0)),
                fee=float(stl_row.get("fee", 0)),
                tax=float(stl_row.get("tax", 0)),
            )
            matches.append(match)
            matched_bank_idx.add(b_idx)
            matched_settlement_idx.add(stl_match_idx)
    
    # Build unmatched DataFrames
    unmatched_bank = bank_df.drop(index=list(matched_bank_idx)) if matched_bank_idx else bank_df.copy()
    unmatched_settlement = settlement_df.drop(index=list(matched_settlement_idx)) if matched_settlement_idx else settlement_df.copy()
    unmatched_ledger = ledger_df.drop(index=list(matched_ledger_idx)) if matched_ledger_idx else ledger_df.copy()
    
    return matches, unmatched_bank, unmatched_settlement, unmatched_ledger


def fuzzy_match(
    unmatched_bank: pd.DataFrame,
    unmatched_settlement: pd.DataFrame,
    unmatched_ledger: pd.DataFrame,
) -> List[MatchResult]:
    """
    Perform weighted fuzzy matching on unmatched records.
    
    Scoring weights:
    - Payment ID similarity (Levenshtein): 35%
    - Amount similarity: 30%
    - Date proximity: 15%
    - Customer/reference similarity: 10%
    - Metadata similarity: 10%
    
    Returns list of MatchResult with confidence scores.
    """
    matches = []
    pay_id_map = create_payment_id_mapping(unmatched_bank)
    
    matched_bank_idx = set()
    matched_settlement_idx = set()
    
    for b_idx, bank_row in unmatched_bank.iterrows():
        if b_idx in matched_bank_idx:
            continue
        
        bank_tx_id = str(bank_row.get("transaction_id", ""))
        bank_pay_id = pay_id_map.get(bank_tx_id, bank_tx_id)
        bank_amount = float(bank_row.get("amount", 0))
        bank_date = _parse_date(str(bank_row.get("transaction_date", "")))
        bank_ref = str(bank_row.get("customer_reference", ""))
        
        best_score = 0.0
        best_match = None
        best_s_idx = None
        best_l_idx = None
        
        # Try matching against settlements
        for s_idx, s_row in unmatched_settlement.iterrows():
            if s_idx in matched_settlement_idx:
                continue
            
            s_pay_id = str(s_row.get("payment_id", ""))
            s_amount = float(s_row.get("gross_amount", 0))
            s_date = _parse_date(str(s_row.get("settlement_date", "")))
            
            # Calculate weighted score
            id_sim = fuzz.ratio(bank_pay_id, s_pay_id)
            amt_sim = _amount_similarity(bank_amount, s_amount)
            date_sim = _date_proximity_score(bank_date, s_date)
            ref_sim = 50.0  # No direct reference in settlement
            meta_sim = 50.0  # Base metadata score
            
            # Weighted score
            score = (
                id_sim * 0.35 +
                amt_sim * 0.30 +
                date_sim * 0.15 +
                ref_sim * 0.10 +
                meta_sim * 0.10
            )
            
            if score > best_score:
                best_score = score
                date_diff = _date_diff_days(bank_date, s_date)
                
                # Find matching ledger for this payment
                ledger_amount = 0.0
                ledger_idx = None
                for l_idx, l_row in unmatched_ledger.iterrows():
                    l_pay_id = str(l_row.get("payment_id", ""))
                    if fuzz.ratio(bank_pay_id, l_pay_id) > 80:
                        ledger_amount = float(l_row.get("expected_amount", 0))
                        ledger_idx = l_idx
                        break
                
                reasons = []
                if id_sim >= 90:
                    reasons.append(f"✓ Payment ID similarity: {id_sim}%")
                else:
                    reasons.append(f"△ Payment ID similarity: {id_sim}%")
                if amt_sim >= 95:
                    reasons.append(f"✓ Amount similarity: {amt_sim}%")
                else:
                    reasons.append(f"△ Amount similarity: {amt_sim}%")
                reasons.append(f"{'✓' if date_sim >= 70 else '△'} Date proximity: {date_diff} day(s)")
                reasons.append(f"Fuzzy weighted score: {score:.1f}/100")
                
                best_match = MatchResult(
                    source_id=bank_tx_id,
                    target_id=str(s_row.get("settlement_id", "")),
                    source_type="bank",
                    target_type="settlement",
                    payment_id=bank_pay_id,
                    confidence=round(score / 100.0, 4),
                    match_type="fuzzy",
                    reasons=reasons,
                    score_breakdown={
                        "payment_id_similarity": round(id_sim, 1),
                        "amount_similarity": round(amt_sim, 1),
                        "date_proximity": round(date_sim, 1),
                        "customer_reference": round(ref_sim, 1),
                        "metadata": round(meta_sim, 1),
                    },
                    amount_difference=round(abs(bank_amount - s_amount), 2),
                    date_difference_days=date_diff,
                    bank_amount=bank_amount,
                    ledger_amount=ledger_amount,
                    settlement_amount=s_amount,
                    settlement_net=float(s_row.get("net_amount", 0)),
                    fee=float(s_row.get("fee", 0)),
                    tax=float(s_row.get("tax", 0)),
                )
                best_s_idx = s_idx
                best_l_idx = ledger_idx
        
        if best_match and best_score > 30:  # Minimum threshold to report
            matches.append(best_match)
            matched_bank_idx.add(b_idx)
            if best_s_idx is not None:
                matched_settlement_idx.add(best_s_idx)
    
    return matches
