# RazorRecon AI — System Architecture & Design Specification

## Overview

RazorRecon AI is an AI-powered financial controller designed for merchant payment operations. It automates financial reconciliation across 5 data sources while enforcing a **Precision First** design philosophy.

---

## Data Pipeline Architecture

```
Data Sources (CSV)
  ├─ Bank Statements
  ├─ Razorpay Settlements
  ├─ Internal Ledger
  ├─ Refunds
  └─ Chargebacks
       │
       ▼
Ingestion & Normalization
  ├─ Type Casting & ISO-8601 Date Parsing
  ├─ Decimal Precision Amounts
  └─ Preserving Original Source Values
       │
       ▼
Matching Pipeline
  ├─ Exact 3-Way Match (Confidence = 1.0)
  └─ Weighted Fuzzy Match (Scores 0 - 100)
       │
       ▼
Confidence Decision Gate
  ├─ Confidence >= 0.90 ──► Auto-Reconciled
  ├─ Confidence 0.75-0.89 ──► AI-Assisted Review
  └─ Confidence < 0.75 ──► Human-in-the-Loop Review Queue
       │
       ▼
Audit Trail & Analytics
  ├─ Immutable Audit Log
  ├─ Held-Out Evaluation Metrics
  └─ Natural Language Controller Chat Engine
```

---

## Key Modules

1. **Normalization Service (`backend/app/services/normalization.py`)**
   - Parses dates into `YYYY-MM-DD` ISO-8601 format
   - Converts monetary amounts to 2-decimal floating point using `Decimal`
   - Strips whitespace and normalizes payment IDs (`PAY_0001`)

2. **Matching Engine (`backend/app/services/matching.py`)**
   - **Exact Matching**: Checks 3-way alignment across Bank, Settlement, and Ledger within date tolerance window.
   - **Weighted Fuzzy Matching**:
     - Payment ID similarity (Levenshtein): 35%
     - Amount similarity: 30%
     - Date proximity: 15%
     - Customer reference similarity: 10%
     - Metadata similarity: 10%

3. **Confidence Gate (`backend/app/services/confidence.py`)**
   - Verifies settlement math: $\text{Gross} - \text{Fee} - \text{Tax} = \text{Net}$.
   - Detects 11 exception types: `MISSING_IN_BANK`, `MISSING_IN_LEDGER`, `MISSING_IN_SETTLEMENT`, `AMOUNT_MISMATCH`, `DATE_MISMATCH`, `DUPLICATE_TRANSACTION`, `PARTIAL_SETTLEMENT`, `REFUND`, `CHARGEBACK`, `FEE_MISMATCH`, `UNKNOWN_EXCEPTION`.

4. **AI Reconciliation Analyst (`backend/app/services/ai_analyst.py`)**
   - Integrates Google Gemini LLM for structured JSON exception reasoning.
   - Pre-computes math deterministically before prompting the LLM.
   - Includes fallback template engine when LLM is unavailable.

5. **Audit Trail Logger (`backend/app/services/audit.py`)**
   - Append-only immutable logging.
   - Records transaction ID, action, reason, confidence, agent, evidence, and rule used.

6. **Evaluation Engine (`backend/app/services/evaluation.py`)**
   - Evaluates performance on held-out synthetic test set.
   - Calculates Precision, Recall, F1 Score, Confusion Matrix, and Financial Exposure (False Positive Cost).
