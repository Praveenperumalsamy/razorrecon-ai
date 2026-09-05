"""
Import test script for RazorRecon AI backend services.
"""

def test_all_imports():
    from app.services.normalization import normalize_dataframe, normalize_id, normalize_amount, normalize_date
    from app.services.matching import exact_match, fuzzy_match, MatchResult
    from app.services.confidence import classify_match, detect_exceptions, verify_settlement_calculation, ReconciliationStatus, ExceptionType
    from app.services.audit import AuditLogger, AuditEntry
    from app.services.exceptions import ExceptionManager
    from app.services.ai_analyst import ReconciliationAnalyst
    from app.services.reconciliation import ReconciliationEngine
    from app.services.evaluation import EvaluationEngine
    from app.services.chat import FinanceController
    
    print("ALL 9 SERVICES IMPORTED SUCCESSFULLY!")

if __name__ == "__main__":
    test_all_imports()
