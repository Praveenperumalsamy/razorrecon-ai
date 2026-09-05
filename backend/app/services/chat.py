
"""
Natural Language Finance Controller Chat Service for RazorRecon AI

Uses real reconciliation data for all financial facts.
Gemini is used to explain verified results in natural language.
NEVER allows Gemini to invent financial numbers.
"""

from typing import Dict, Any, Optional
import re
from datetime import datetime, timezone

from .ai_analyst import ReconciliationAnalyst


class FinanceController:
    """
    Natural Language Finance Controller Chat Engine.
    """

    def __init__(self, ai_analyst: Optional[ReconciliationAnalyst] = None):
        self.ai = ai_analyst or ReconciliationAnalyst()

    def _gemini_explain(
        self,
        question: str,
        verified_data: Dict[str, Any],
        default_response: str,
    ) -> str:
        """
        Ask Gemini to explain VERIFIED financial data.

        Gemini must not calculate or invent financial figures.
        """

        if not self.ai.use_llm:
            return default_response

        prompt = f"""
You are RazorRecon AI, a fintech reconciliation assistant.

Answer the user's question using ONLY the VERIFIED DATA below.

IMPORTANT RULES:
1. Never invent financial numbers.
2. Never change any number from the verified data.
3. Never create transactions, payment IDs, amounts, or statuses.
4. If information is missing, explicitly say it is unavailable.
5. Keep the answer concise and professional.
6. Currency is INR unless the verified data says otherwise.
7. Explain the result clearly for a finance operations user.

USER QUESTION:
{question}

VERIFIED DATA:
{verified_data}

BASE VERIFIED ANSWER:
{default_response}

Return only the final natural-language answer.
"""

        try:
            answer = self.ai.generate_text(prompt)

            if answer:
                return answer.strip()

        except Exception:
            pass

        return default_response

    def answer(
        self,
        question: str,
        reconciliation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        q = question.strip().lower()
        now_str = datetime.now(timezone.utc).isoformat()

        results = reconciliation_data or {}

        summary = results.get("summary", {})
        transactions = results.get("transactions", [])
        exceptions = results.get("exceptions", [])

        # ---------------------------------------------------------
        # 1. UNRECONCILED AMOUNT
        # ---------------------------------------------------------

        if "unreconciled" in q or "unresolved" in q:

            # Human-review transactions are the authoritative source.
            pending_txs = [
                t for t in transactions
                if t.get("status") == "human_review"
            ]

            # Prefer actual difference when available.
            total_unrec = 0.0

            for tx in pending_txs:

                if tx.get("difference") is not None:
                    try:
                        total_unrec += abs(float(tx.get("difference") or 0))
                    except (ValueError, TypeError):
                        pass

                elif tx.get("bank_amount") is not None:
                    try:
                        total_unrec += abs(float(tx.get("bank_amount") or 0))
                    except (ValueError, TypeError):
                        pass

            count = len(pending_txs)

            verified = {
                "unreconciled_amount": round(total_unrec, 2),
                "pending_human_review_transactions": count,
                "currency": "INR",
            }

            base = (
                f"There is currently **₹{total_unrec:,.2f}** "
                f"unreconciled across **{count}** pending transactions "
                f"requiring human review."
            )

            content = self._gemini_explain(
                question,
                verified,
                base
            )

            return {
                "role": "assistant",
                "content": content,
                "data": verified,
                "sources": [
                    "reconciliation_database",
                    "reconciliation_engine",
                    "gemini"
                ],
                "timestamp": now_str,
            }

        # ---------------------------------------------------------
        # 2. SPECIFIC TRANSACTION
        # ---------------------------------------------------------

        pay_match = re.search(
            r"(pay_\d+|btx_\d+|stl_\d+|led_\d+)",
            q
        )

        if pay_match or "why is" in q or "different" in q:

            target_id = (
                pay_match.group(1).upper()
                if pay_match
                else ""
            )

            found_tx = None

            for tx in transactions:

                payment_id = str(
                    tx.get("payment_id", "")
                ).upper()

                tx_id = str(
                    tx.get("id", "")
                ).upper()

                if target_id and (
                    target_id == payment_id
                    or target_id == tx_id
                ):
                    found_tx = tx
                    break

            if found_tx:

                verified = {
                    "payment_id": found_tx.get("payment_id"),
                    "bank_amount": found_tx.get("bank_amount"),
                    "settlement_amount": found_tx.get(
                        "settlement_amount"
                    ),
                    "difference": found_tx.get("difference"),
                    "confidence": found_tx.get("confidence"),
                    "status": found_tx.get("status"),
                    "exception_type": found_tx.get(
                        "exception_type"
                    ),
                }

                base = (
                    f"Transaction **{found_tx.get('payment_id')}** "
                    f"has status **{found_tx.get('status')}** "
                    f"with a reconciliation difference of "
                    f"**₹{float(found_tx.get('difference') or 0):,.2f}**."
                )

                content = self._gemini_explain(
                    question,
                    verified,
                    base
                )

                return {
                    "role": "assistant",
                    "content": content,
                    "data": found_tx,
                    "sources": [
                        "reconciliation_database",
                        "reconciliation_engine",
                        "gemini"
                    ],
                    "timestamp": now_str,
                }

        # ---------------------------------------------------------
        # 3. HIGHEST-RISK EXCEPTIONS
        # ---------------------------------------------------------

        if (
            "highest-risk" in q
            or "highest risk" in q
            or "risk" in q
            or "exceptions" in q
        ):

            pending = [
                e for e in exceptions
                if e.get("status") == "pending"
            ]

            sorted_exc = sorted(
                pending,
                key=lambda x: abs(
                    float(x.get("difference") or 0)
                ),
                reverse=True
            )[:5]

            verified = {
                "count": len(sorted_exc),
                "exceptions": sorted_exc,
            }

            if sorted_exc:

                lines = [
                    "Top highest-risk unresolved exceptions:"
                ]

                for idx, exc in enumerate(
                    sorted_exc,
                    1
                ):
                    lines.append(
                        f"{idx}. "
                        f"{exc.get('payment_id')} — "
                        f"Difference: ₹"
                        f"{float(exc.get('difference') or 0):,.2f} — "
                        f"Type: {exc.get('exception_type')} — "
                        f"Action: {exc.get('recommended_action')}"
                    )

                base = "\n".join(lines)

            else:
                base = "No pending high-risk exceptions found."

            content = self._gemini_explain(
                question,
                verified,
                base
            )

            return {
                "role": "assistant",
                "content": content,
                "data": sorted_exc,
                "sources": [
                    "exceptions_queue",
                    "gemini"
                ],
                "timestamp": now_str,
            }

        # ---------------------------------------------------------
        # 4. RECONCILIATION STATISTICS
        # ---------------------------------------------------------

        if (
            "auto-reconciled" in q
            or "auto reconciled" in q
            or "match rate" in q
            or "statistics" in q
            or "how many payments" in q
        ):

            auto_c = summary.get(
                "auto_reconciled",
                0
            )

            rate = summary.get(
                "match_rate",
                0
            )

            total = summary.get(
                "total_records",
                0
            )

            auto_rate = summary.get(
                "auto_reconciliation_rate",
                0
            )

            verified = {
                "total_records": total,
                "auto_reconciled": auto_c,
                "auto_reconciliation_rate": auto_rate,
                "match_rate": rate,
            }

            base = (
                f"Out of **{total}** total ingested records, "
                f"**{auto_c}** payments "
                f"({auto_rate}%) were automatically reconciled. "
                f"The overall match rate is **{rate}%**."
            )

            content = self._gemini_explain(
                question,
                verified,
                base
            )

            return {
                "role": "assistant",
                "content": content,
                "data": verified,
                "sources": [
                    "reconciliation_summary",
                    "gemini"
                ],
                "timestamp": now_str,
            }

        # ---------------------------------------------------------
        # 5. GENERAL GEMINI FINANCE ASSISTANT
        # ---------------------------------------------------------

        if self.ai.use_llm:

            verified = {
                "summary": summary,
                "transaction_count": len(transactions),
                "exception_count": len(exceptions),
            }

            content = self._gemini_explain(
                question,
                verified,
                (
                    "I am RazorRecon AI. "
                    "I can analyze reconciliation results, "
                    "exceptions, transaction differences, "
                    "unreconciled amounts, and match rates."
                )
            )

            return {
                "role": "assistant",
                "content": content,
                "data": summary,
                "sources": [
                    "reconciliation_database",
                    "gemini"
                ],
                "timestamp": now_str,
            }

        # ---------------------------------------------------------
        # 6. NO GEMINI FALLBACK
        # ---------------------------------------------------------

        return {
            "role": "assistant",
            "content": (
                f"The financial system currently has "
                f"**{summary.get('total_records', 0)}** records "
                f"with an overall match rate of "
                f"**{summary.get('match_rate', 0)}%**."
            ),
            "data": summary,
            "sources": ["reconciliation_database"],
            "timestamp": now_str,
        }

