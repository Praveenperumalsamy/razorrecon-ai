"""
Reconciliation Pipeline Orchestrator for RazorRecon AI

Coordinates the 5-step financial reconciliation workflow:
Step 1: Data Ingestion & Validation
Step 2: Normalization (IDs, dates, amounts, preserving originals)
Step 3: Exact Deterministic Matching (Confidence = 1.0)
Step 4: Weighted Fuzzy Matching (Scores 0-100)
Step 5: Confidence Gate & Exception Agent Analysis
"""

import time
from typing import Dict, Any, List, Optional, Callable
import pandas as pd

from .normalization import normalize_dataframe
from .matching import exact_match, fuzzy_match, MatchResult
from .confidence import classify_match, detect_exceptions, verify_settlement_calculation, ReconciliationStatus
from .audit import AuditLogger
from .exceptions import ExceptionManager
from .ai_analyst import ReconciliationAnalyst


class ReconciliationEngine:
    """
    Main Autonomous Financial Reconciliation Controller.
    """
    
    def __init__(
        self,
        config: Optional[dict] = None,
        audit_logger: AuditLogger = None,
        exception_manager: ExceptionManager = None,
        ai_analyst: Optional[ReconciliationAnalyst] = None,
    ):
        if audit_logger is None or exception_manager is None:
            raise ValueError(
                "ReconciliationEngine requires an explicit AuditLogger and "
                "ExceptionManager bound to a DB session (both are now "
                "DB-persisted and need a `db: Session` — see app/main.py's "
                "_build_engine() for the standard construction pattern)."
            )
        self.config = config or {}
        self.audit = audit_logger
        self.exceptions = exception_manager
        self.ai = ai_analyst or ReconciliationAnalyst()
        
        self.auto_threshold = float(self.config.get("AUTO_RECONCILE_THRESHOLD", 0.90))
        self.review_threshold = float(self.config.get("AI_REVIEW_THRESHOLD", 0.75))
        self.date_tolerance_days = int(self.config.get("DATE_TOLERANCE_DAYS", 3))
        
        self.last_results: Dict[str, Any] = {}
        
    def run(
        self,
        bank_df: pd.DataFrame,
        settlement_df: pd.DataFrame,
        ledger_df: pd.DataFrame,
        refund_df: Optional[pd.DataFrame] = None,
        chargeback_df: Optional[pd.DataFrame] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full multi-stage reconciliation pipeline.
        """
        start_time = time.time()
        
        refund_df = refund_df if refund_df is not None else pd.DataFrame()
        chargeback_df = chargeback_df if chargeback_df is not None else pd.DataFrame()
        
        if progress_callback: progress_callback("STEP 1: Data Ingestion & Validation", 10)
        
        # Ingestion counts
        ingestion_summary = {
            "bank_records": len(bank_df),
            "settlement_records": len(settlement_df),
            "ledger_records": len(ledger_df),
            "refund_records": len(refund_df),
            "chargeback_records": len(chargeback_df),
            "total_ingested": len(bank_df) + len(settlement_df) + len(ledger_df) + len(refund_df) + len(chargeback_df),
        }
        
        if progress_callback: progress_callback("STEP 2: Data Normalization", 30)
        
        # Step 2: Normalization
        norm_bank = normalize_dataframe(bank_df, "bank")
        norm_settlement = normalize_dataframe(settlement_df, "settlement")
        norm_ledger = normalize_dataframe(ledger_df, "ledger")
        norm_refund = normalize_dataframe(refund_df, "refund")
        norm_chargeback = normalize_dataframe(chargeback_df, "chargeback")
        
        if progress_callback: progress_callback("STEP 3: Exact Deterministic Matching", 50)
        
        # Step 3: Exact Matching
        exact_matches, un_bank, un_settle, un_ledger = exact_match(
            norm_bank, norm_settlement, norm_ledger, date_tolerance_days=self.date_tolerance_days
        )
        
        # Log exact matches to audit trail
        for match in exact_matches:
            status = classify_match(match.confidence, self.auto_threshold, self.review_threshold)
            self.audit.log(
                transaction_id=match.source_id,
                action="AUTO_RECONCILED" if status == ReconciliationStatus.AUTO_RECONCILED else "EXACT_MATCH_FOUND",
                reason="; ".join(match.reasons),
                confidence=match.confidence,
                agent="ReconciliationEngine",
                details=match.to_dict(),
                rule_used="EXACT_MATCH_RULE",
            )
            
        if progress_callback: progress_callback("STEP 4: Weighted Fuzzy Matching", 70)
        
        # Step 4: Fuzzy Matching
        fuzzy_matches = fuzzy_match(un_bank, un_settle, un_ledger)
        all_matches = exact_matches + fuzzy_matches
        matched_payment_ids = {m.payment_id for m in all_matches}
        
        if progress_callback: progress_callback("STEP 5: Exception Analysis & Decision Gate", 90)
        
        # Step 5: Decision Gate & Exception Processing
        classified_transactions = []
        auto_count = 0
        ai_review_count = 0
        human_review_count = 0
        
        for match in all_matches:
            status = classify_match(match.confidence, self.auto_threshold, self.review_threshold)
            
            # Form transaction item
            tx_item = {
                "id": match.source_id,
                "payment_id": match.payment_id,
                "bank_amount": match.bank_amount,
                "ledger_amount": match.ledger_amount,
                "settlement_amount": match.settlement_amount,
                "status": status.value,
                "confidence": match.confidence,
                "match_type": match.match_type,
                "reasons": match.reasons,
                "score_breakdown": match.score_breakdown,
                "amount_difference": match.amount_difference,
                "date_difference_days": match.date_difference_days,
                "currency": "INR",
                "date": str(norm_bank[norm_bank["transaction_id"] == match.source_id]["transaction_date"].values[0]) if not norm_bank.empty and "transaction_date" in norm_bank.columns and match.source_id in norm_bank["transaction_id"].values else "",
            }
            
            if status == ReconciliationStatus.AUTO_RECONCILED:
                auto_count += 1
            elif status == ReconciliationStatus.AI_REVIEW:
                ai_review_count += 1
                # AI Analyst provides reasoning for AI review items
                ai_res = self.ai.analyze_exception(
                    tx_item,
                    possible_matches=[match.to_dict()],
                    settlement_data={"gross_amount": match.settlement_amount, "fee": match.fee, "tax": match.tax, "net_amount": match.settlement_net}
                )
                tx_item["ai_explanation"] = ai_res.get("reason", "")
                tx_item["ai_evidence"] = ai_res.get("evidence", [])
            else:
                human_review_count += 1
                # Register in exception queue
                ai_res = self.ai.analyze_exception(
                    tx_item,
                    possible_matches=[match.to_dict()],
                    settlement_data={"gross_amount": match.settlement_amount, "fee": match.fee, "tax": match.tax, "net_amount": match.settlement_net}
                )
                self.exceptions.register_exception(
                    transaction_id=match.source_id,
                    payment_id=match.payment_id,
                    exception_type="UNCONFIRMED_MATCH",
                    expected_amount=match.bank_amount,
                    actual_amount=match.settlement_amount,
                    difference=match.amount_difference,
                    date_difference_days=match.date_difference_days,
                    details=match.to_dict(),
                    possible_matches=[match.to_dict()],
                    ai_analysis=ai_res
                )
                tx_item["ai_explanation"] = ai_res.get("reason", "")
                tx_item["ai_evidence"] = ai_res.get("evidence", [])

            classified_transactions.append(tx_item)

        # Detect non-match exceptions across sources
        raw_exceptions = detect_exceptions(
            norm_bank, norm_settlement, norm_ledger, norm_refund, norm_chargeback, matched_payment_ids
        )
        
        for exc in raw_exceptions:
            human_review_count += 1
            ai_res = self.ai.analyze_exception(exc, possible_matches=[])
            self.exceptions.register_exception(
                transaction_id=exc["transaction_id"],
                payment_id=exc["payment_id"],
                exception_type=exc["exception_type"],
                expected_amount=exc["expected_amount"],
                actual_amount=exc["actual_amount"],
                difference=exc["difference"],
                date_difference_days=exc["date_difference_days"],
                details=exc.get("details", {}),
                ai_analysis=ai_res
            )

        elapsed_time = round(time.time() - start_time, 2)
        total_records = len(norm_bank)
        reconciled_count = auto_count + ai_review_count
        
        # Sum total & reconciled amounts
        total_amount = sum(t["bank_amount"] for t in classified_transactions)
        reconciled_amount = sum(t["bank_amount"] for t in classified_transactions if t["status"] in ("auto_reconciled", "ai_review"))

        if progress_callback: progress_callback("COMPLETE: Reconciliation Finished", 100)

        results = {
            "summary": {
                "total_records": total_records,
                "reconciled": reconciled_count,
                "auto_reconciled": auto_count,
                "ai_assisted": ai_review_count,
                "human_review": human_review_count,
                "exceptions": len(self.exceptions.get_all()),
                "match_rate": round((reconciled_count / total_records * 100), 1) if total_records else 0,
                "auto_reconciliation_rate": round((auto_count / total_records * 100), 1) if total_records else 0,
                "exception_rate": round((human_review_count / total_records * 100), 1) if total_records else 0,
                "total_amount": round(total_amount, 2),
                "reconciled_amount": round(reconciled_amount, 2),
                "currency": "INR",
                "execution_time_seconds": elapsed_time,
            },
            "ingestion_summary": ingestion_summary,
            "transactions": classified_transactions,
            "exceptions": self.exceptions.get_all(),
            "audit_trail": self.audit.get_recent(100),
            "dataframes": {
                "bank": norm_bank,
                "settlement": norm_settlement,
                "ledger": norm_ledger,
                "refund": norm_refund,
                "chargeback": norm_chargeback,
            }
        }
        
        self.last_results = results
        return results
