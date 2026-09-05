export interface DashboardData {
  total_records: number;
  reconciled: number;
  auto_reconciled: number;
  ai_assisted: number;
  human_review: number;
  exceptions: number;
  match_rate: number;
  auto_reconciliation_rate: number;
  exception_rate: number;
  total_amount: number;
  reconciled_amount: number;
  currency: string;
}

export interface Transaction {
  id: string;
  payment_id: string;
  bank_amount: number;
  ledger_amount: number;
  settlement_amount: number;

  status:
    | 'auto_reconciled'
    | 'ai_review'
    | 'human_review'
    | 'manually_approved'
    | 'manually_rejected'
    | 'exception';

  confidence: number;
  match_type: string;
  exception_type?: string;
  ai_explanation?: string;
  ai_evidence?: string[];
  reasons?: string[];
  score_breakdown?: Record<string, number>;
  amount_difference?: number;
  date_difference_days?: number;
date: string;
  currency: string;
}

export interface ExceptionItem {
  id: string;
  transaction_id: string;
  payment_id: string;
  exception_type: string;
  expected_amount: number;
  actual_amount: number;
  difference: number;
  date_difference_days: number;
  currency?: string;
  details: Record<string, any>;
  possible_matches: any[];
  ai_confidence: number;
  ai_explanation: string;
  ai_evidence: string[];
  recommended_action: string;
  status: 'pending' | 'approved' | 'rejected' | 'escalated';
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  transaction_id: string;
  action: string;
  reason: string;
  confidence: number;
  agent: string;
  details?: Record<string, any>;
  rule_used?: string;
}

export interface EvaluationData {
  precision: number;
  recall: number;
  f1_score: number;
  match_rate: number;
  auto_reconciliation_rate: number;
  exception_rate: number;
  false_positive_rate: number;
  false_positive_count: number;
  false_positive_amount: number;

  confusion_matrix: {
    true_positives: number;
    false_positives: number;
    true_negatives: number;
    false_negatives: number;
  };

  amount_reconciliation_rate: number;
  total_amount: number;
  reconciled_amount: number;
  currency: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  data?: any;
  sources?: string[];
  timestamp: string;
}

/* =========================================
   Transaction Detail
   ========================================= */

export interface TransactionDetail {
  transaction: Transaction;

  ai_analysis: {
    confidence: number;
    classification: string;
    reason: string;
    evidence: string[];
    requires_human_review: boolean;
    recommended_action: string;
  } | null;

  score_breakdown: Record<string, number>;

  bank_record: Record<string, any> | null;

  ledger_record: Record<string, any> | null;

  settlement_record: Record<string, any> | null;

  audit_history: AuditEntry[];
}