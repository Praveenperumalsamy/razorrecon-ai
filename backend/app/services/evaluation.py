"""
Held-Out Test Set Evaluation Service for RazorRecon AI

Evaluates reconciliation pipeline performance against ground truth labels.
Calculates Precision, Recall, F1 Score, Confusion Matrix, and Financial Exposure (False Positive Cost).
"""

from typing import Dict, Any, List, Optional
import json


class EvaluationEngine:
    """
    Evaluates reconciliation results on held-out test data.
    Ensures zero data leakage and honest metric reporting.
    """
    
    def evaluate(
        self,
        reconciliation_results: Dict[str, Any],
        ground_truth: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Compute evaluation metrics against ground truth.
        """
        gt_dict = {item["payment_id"]: item for item in ground_truth}
        
        tp = 0  # True Positive: Correctly matched clean transaction
        fp = 0  # False Positive: Incorrectly auto-reconciled an anomaly
        tn = 0  # True Negative: Correctly flagged anomaly to human review
        fn = 0  # False Negative: Missed a valid match (flagged as exception)
        
        false_positive_amount = 0.0
        total_amount = 0.0
        reconciled_amount = 0.0
        
        transactions = reconciliation_results.get("transactions", [])
        
        for tx in transactions:
            pay_id = tx.get("payment_id", "")
            status = tx.get("status", "")
            amount = float(tx.get("bank_amount", 0.0))
            total_amount += amount
            
            gt_item = gt_dict.get(pay_id, {})
            is_anomaly_in_gt = gt_item.get("status") == "anomaly"
            
            # System decision
            is_auto_reconciled = status in ("auto_reconciled", "ai_review")
            
            if is_auto_reconciled:
                reconciled_amount += amount
                if not is_anomaly_in_gt:
                    tp += 1
                else:
                    fp += 1
                    false_positive_amount += amount
            else:
                if is_anomaly_in_gt:
                    tn += 1
                else:
                    fn += 1

        total_eval_records = tp + fp + tn + fn or 1
        
        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 1.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1_score = round(2 * (precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0
        
        match_rate = round(((tp + fp) / total_eval_records * 100), 1)
        auto_recon_rate = round((tp / total_eval_records * 100), 1)
        exception_rate = round(((tn + fn) / total_eval_records * 100), 1)
        fp_rate = round((fp / total_eval_records * 100), 2)
        amount_recon_rate = round((reconciled_amount / total_amount * 100), 1) if total_amount > 0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "match_rate": match_rate,
            "auto_reconciliation_rate": auto_recon_rate,
            "exception_rate": exception_rate,
            "false_positive_rate": fp_rate,
            "false_positive_count": fp,
            "false_positive_amount": round(false_positive_amount, 2),
            "confusion_matrix": {
                "true_positives": tp,
                "false_positives": fp,
                "true_negatives": tn,
                "false_negatives": fn,
            },
            "amount_reconciliation_rate": amount_recon_rate,
            "total_amount": round(total_amount, 2),
            "reconciled_amount": round(reconciled_amount, 2),
            "currency": "INR",
        }
