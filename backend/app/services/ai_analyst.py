"""
AI Reconciliation Analyst Service for RazorRecon AI

Combines Google Gemini LLM reasoning with deterministic pre-computation.

CRITICAL DESIGN PRINCIPLE:
Financial calculations are performed deterministically FIRST.
The LLM is used ONLY for:
- Interpreting ambiguous discrepancies
- Generating human-readable reconciliation explanations
- Categorizing complex exception edge-cases
- Recommending next actions
- Prioritizing exceptions

Returns structured JSON output.
"""

import os
import json
from typing import Optional, Dict, Any, List

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from .confidence import ExceptionType, verify_settlement_calculation


class ReconciliationAnalyst:
    """
    AI Reconciliation Analyst that interprets financial discrepancies.
    Uses Google Gemini when available, with a deterministic template fallback.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.use_llm = bool(self.api_key) and (genai is not None)
        
        if self.use_llm:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception as e:
                print(f"Warning: Gemini init failed: {e}. Falling back to template AI.")
                self.use_llm = False
    
    def analyze_exception(
        self,
        transaction_data: Dict[str, Any],
        possible_matches: Optional[List[Dict[str, Any]]] = None,
        settlement_data: Optional[Dict[str, Any]] = None,
        refund_data: Optional[Dict[str, Any]] = None,
        chargeback_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze an exception using pre-computed deterministic facts + AI reasoning.
        
        Returns:
            {
                "classification": str,
                "confidence": float,
                "reason": str,
                "evidence": List[str],
                "recommended_action": str,
                "requires_human_review": bool,
                "calculation_verification": dict
            }
        """
        possible_matches = possible_matches or []
        
        # 1. ALWAYS perform deterministic pre-computation first
        calc_verification = {}
        if settlement_data:
            gross = float(settlement_data.get("gross_amount", 0))
            fee = float(settlement_data.get("fee", 0))
            tax = float(settlement_data.get("tax", 0))
            net = float(settlement_data.get("net_amount", 0))
            calc_verification = verify_settlement_calculation(gross, fee, tax, net)
        
        # 2. If Gemini LLM is enabled, call LLM with pre-computed facts
        if self.use_llm:
            try:
                prompt = self._build_prompt(
                    transaction_data, possible_matches, settlement_data,
                    refund_data, chargeback_data, calc_verification
                )
                response = self.model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                parsed = json.loads(response.text)
                parsed["calculation_verification"] = calc_verification
                return parsed
            except Exception as e:
                print(f"LLM call failed: {e}. Using deterministic fallback analysis.")
        
        # 3. Fallback: Deterministic template reasoning (fast & guaranteed reliable)
        return self._fallback_analysis(
            transaction_data, possible_matches, settlement_data,
            refund_data, chargeback_data, calc_verification
        )

    def generate_text(self, prompt: str) -> Optional[str]:
        """
        Free-form Gemini text generation for natural-language explanations
        (e.g. the chat assistant). Unlike analyze_exception(), this does NOT
        force a structured exception-classification JSON schema — it's for
        plain conversational answers over already-verified data.

        Returns None (never a fabricated string) if the LLM is unavailable
        or the call fails, so callers can fall back to their own
        deterministic, verified-data-backed response.
        """
        if not self.use_llm:
            return None

        try:
            response = self.model.generate_content(prompt)
            text = (response.text or "").strip()
            return text or None
        except Exception as e:
            print(f"Gemini text generation failed: {e}. Using deterministic fallback response.")
            return None
    
    def _build_prompt(
        self,
        tx_data: dict,
        matches: list,
        settlement: Optional[dict],
        refund: Optional[dict],
        chargeback: Optional[dict],
        calc: dict,
    ) -> str:
        """Build structured prompt instructing the LLM to output pure JSON."""
        return f"""You are the RazorRecon AI Finance Controller. Analyze this financial exception.
DO NOT perform mathematical calculations yourself. Use the pre-computed financial verification provided below.

--- TRANSACTION DATA ---
{json.dumps(tx_data, indent=2)}

--- SETTLEMENT DATA ---
{json.dumps(settlement or {}, indent=2)}

--- PRE-COMPUTED VERIFICATION (DETERMINISTIC MATH) ---
{json.dumps(calc, indent=2)}

--- REFUND / CHARGEBACK DATA ---
Refund: {json.dumps(refund or {}, indent=2)}
Chargeback: {json.dumps(chargeback or {}, indent=2)}

--- POSSIBLE MATCHES ---
{json.dumps(matches, indent=2)}

Output ONLY valid JSON matching this schema:
{{
  "classification": "<one of: AMOUNT_MISMATCH, DATE_MISMATCH, MISSING_IN_BANK, MISSING_IN_LEDGER, MISSING_IN_SETTLEMENT, DUPLICATE_TRANSACTION, PARTIAL_SETTLEMENT, REFUND, CHARGEBACK, FEE_MISMATCH, UNKNOWN_EXCEPTION>",
  "confidence": <float between 0.0 and 1.0>,
  "reason": "<clear 1-2 sentence human readable explanation>",
  "evidence": ["<evidence point 1>", "<evidence point 2>"],
  "recommended_action": "<one of: AUTO_RECONCILE, HUMAN_REVIEW, APPROVE, REJECT, INVESTIGATE>",
  "requires_human_review": <boolean>
}}"""

    def _fallback_analysis(
        self,
        tx_data: dict,
        matches: list,
        settlement: Optional[dict],
        refund: Optional[dict],
        chargeback: Optional[dict],
        calc: dict,
    ) -> dict:
        """
        Sophisticated deterministic fallback reasoning.
        Translates pre-computed math into structured AI explanation.
        """
        pay_id = tx_data.get("payment_id") or tx_data.get("transaction_id", "")
        
        # Check refund
        if refund:
            return {
                "classification": ExceptionType.REFUND.value,
                "confidence": 0.95,
                "reason": f"Payment {pay_id} has a recorded refund of ₹{refund.get('refund_amount', 0):,.2f} on {refund.get('refund_date', '')} (Reason: {refund.get('reason', 'N/A')}).",
                "evidence": [
                    f"Refund ID: {refund.get('refund_id')}",
                    f"Refund Amount: ₹{refund.get('refund_amount', 0):,.2f}",
                    f"Refund Reason: {refund.get('reason')}",
                ],
                "recommended_action": "APPROVE_REFUND_ADJUSTMENT",
                "requires_human_review": False,
                "calculation_verification": calc,
            }
            
        # Check chargeback
        if chargeback:
            return {
                "classification": ExceptionType.CHARGEBACK.value,
                "confidence": 0.95,
                "reason": f"Payment {pay_id} has a chargeback filed for ₹{chargeback.get('amount', 0):,.2f} on {chargeback.get('chargeback_date', '')} (Reason: {chargeback.get('reason', 'N/A')}).",
                "evidence": [
                    f"Chargeback ID: {chargeback.get('chargeback_id')}",
                    f"Disputed Amount: ₹{chargeback.get('amount', 0):,.2f}",
                    f"Reason: {chargeback.get('reason')}",
                ],
                "recommended_action": "HUMAN_REVIEW",
                "requires_human_review": True,
                "calculation_verification": calc,
            }

        # Check settlement calculation
        if calc and calc.get("valid"):
            gross = calc.get("gross_amount", 0)
            fee = calc.get("fee", 0)
            tax = calc.get("tax", 0)
            return {
                "classification": "RECONCILED",
                "confidence": 0.99,
                "reason": calc.get("explanation", f"Gross amount ₹{gross:,.2f} minus fee ₹{fee:,.2f} and tax ₹{tax:,.2f} matches net settlement."),
                "evidence": [
                    f"Gross Payment: ₹{gross:,.2f}",
                    f"Processing Fee: ₹{fee:,.2f}",
                    f"GST/Tax: ₹{tax:,.2f}",
                    f"Net Settlement: ₹{calc.get('actual_net', 0):,.2f}",
                ],
                "recommended_action": "AUTO_RECONCILE",
                "requires_human_review": False,
                "calculation_verification": calc,
            }
        elif calc and not calc.get("valid"):
            diff = abs(calc.get("difference", 0))
            is_partial = diff > 5.0
            cls = ExceptionType.PARTIAL_SETTLEMENT.value if is_partial else ExceptionType.FEE_MISMATCH.value
            return {
                "classification": cls,
                "confidence": 0.88,
                "reason": calc.get("explanation", f"Settlement discrepancy of ₹{diff:,.2f} detected."),
                "evidence": [
                    f"Expected Net Settlement: ₹{calc.get('expected_net', 0):,.2f}",
                    f"Actual Net Settlement: ₹{calc.get('actual_net', 0):,.2f}",
                    f"Unexplained Variance: ₹{diff:,.2f}",
                ],
                "recommended_action": "HUMAN_REVIEW",
                "requires_human_review": True,
                "calculation_verification": calc,
            }
            
        # Default missing / ambiguous case
        return {
            "classification": ExceptionType.UNKNOWN_EXCEPTION.value,
            "confidence": 0.65,
            "reason": f"Discrepancy detected for {pay_id}. Multiple factors or missing records require human review.",
            "evidence": [f"Payment ID: {pay_id}", f"Matches Evaluated: {len(matches)}"],
            "recommended_action": "HUMAN_REVIEW",
            "requires_human_review": True,
            "calculation_verification": calc,
        }