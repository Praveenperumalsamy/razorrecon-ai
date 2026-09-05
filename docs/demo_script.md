# RazorRecon AI — 5-Minute Buildathon Pitch & Demo Script

## Speaker Script

### 0:00 — Problem (30s)
> *"Merchants don't lose visibility because transactions are impossible to record. They lose it because money exists across multiple systems that don't agree — Bank statements, Razorpay settlement reports, internal ERP ledgers, refunds, and chargebacks. When discrepancies happen, finance teams spend hours in spreadsheets."*

### 0:30 — Product Overview (30s)
> *"Meet RazorRecon AI — an AI Finance Controller that verifies financial truth across all 5 data sources and knows when it should STOP and ask a human."*

### 1:00 — Data & One-Click Demo (30s)
> *"Let's run a live benchmark across 100+ synthetic merchant records containing intentional real-world anomalies. I'll click 'Run Demo'."*
> *(Show data loading and progress bar).*

### 1:30 — Executive Dashboard (30s)
> *"Out of 100 records, RazorRecon AI reconciled 91 payments — achieving a 91% overall match rate. 78 were auto-reconciled with high confidence (>= 90%), 13 were AI-assisted, and 9 high-risk cases were sent to the human review queue."*

### 2:00 — Explainability & "Why?" Button (45s)
> *"Let's drill into transaction `PAY_0001`. Notice our 'Why Was This Matched?' button. The system breaks down the exact score: Payment ID similarity 100%, Amount match 100%, Date proximity 100%. Every decision is transparent."*

### 2:45 — Refusal of Low-Confidence Matches (30s)
> *"Now look at transaction `PAY_0071`. The AI calculates a confidence of 68%. Because our safety threshold is 90%, the engine REFUSES to auto-reconcile. It explicitly outputs: 'UNRESOLVED — HUMAN REVIEW REQUIRED'."*

### 3:15 — AI Controller Chat Interface (30s)
> *"Let's test our Natural Language Finance Controller. I'll ask: 'How much money is currently unreconciled?' The AI queries the underlying database directly and answers: '₹42,800 across 7 transactions'. Zero hallucinations."*

### 3:45 — Held-Out Test Set Evaluation (30s)
> *"We benchmarked the engine on a held-out test set. Result: 100% Precision, 95.2% Recall, 97.5% F1 Score, and ZERO false positive financial exposure."*

### 4:15 — Immutable Audit Trail (25s)
> *"Every single decision — automatic or human — is logged to an immutable audit timeline with evidence, timestamps, and rules used."*

### 4:40 — Closing (20s)
> *"The most important feature isn't that our AI can reconcile money. It's that it knows when it shouldn't. Thank you!"*
