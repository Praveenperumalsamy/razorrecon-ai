"""
Razorpay live API integration.

Replaces the synthetic `razorpay_settlements.csv` fixture with real data
pulled from Razorpay's Settlements & Payments APIs, plus verified webhook
ingestion for near-real-time updates.

Requires RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET (from the Razorpay Dashboard
-> Settings -> API Keys) and RAZORPAY_WEBHOOK_SECRET (Settings -> Webhooks)
to be configured. If they are not set, this client raises
RazorpayNotConfiguredError — callers should fall back to CSV upload mode
rather than crash, since not every deployment needs live PSP access wired
in immediately.
"""

import hashlib
import hmac
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import razorpay
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger("razorrecon.razorpay")


class RazorpayNotConfiguredError(RuntimeError):
    pass


class RazorpayAPIError(RuntimeError):
    pass


def _get_client() -> "razorpay.Client":
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise RazorpayNotConfiguredError(
            "RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are not set. "
            "Configure live API credentials or use CSV upload / demo mode instead."
        )
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    client.set_app_details({"title": settings.APP_NAME, "version": settings.APP_VERSION})
    return client


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((razorpay.errors.ServerError, ConnectionError, TimeoutError)),
)
def fetch_settlements(count: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Pull real settlement records from Razorpay's Settlements API.
    https://razorpay.com/docs/api/settlements/
    """
    client = _get_client()
    try:
        response = client.settlement.all({"count": min(count, 100), "skip": skip})
        return response.get("items", [])
    except razorpay.errors.BadRequestError as e:
        raise RazorpayAPIError(f"Razorpay rejected the settlements request: {e}") from e


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((razorpay.errors.ServerError, ConnectionError, TimeoutError)),
)
def fetch_payments(count: int = 100, skip: int = 0, from_ts: Optional[int] = None, to_ts: Optional[int] = None) -> List[Dict[str, Any]]:
    """Pull real payment records for cross-referencing against bank/ledger data."""
    client = _get_client()
    params: Dict[str, Any] = {"count": min(count, 100), "skip": skip}
    if from_ts:
        params["from"] = from_ts
    if to_ts:
        params["to"] = to_ts
    try:
        response = client.payment.all(params)
        return response.get("items", [])
    except razorpay.errors.BadRequestError as e:
        raise RazorpayAPIError(f"Razorpay rejected the payments request: {e}") from e


def settlements_to_dataframe(items: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Normalize the Razorpay Settlements API response into the same column
    shape the reconciliation engine expects from `razorpay_settlements.csv`,
    so the matching/normalization pipeline needs no changes to consume
    live data instead of the synthetic fixture.
    """
    rows = []
    for item in items:
        rows.append(
            {
                "payment_id": item.get("id", ""),
                "gross_amount": (item.get("amount", 0) or 0) / 100.0,  # paise -> rupees
                "fee": (item.get("fees", 0) or 0) / 100.0,
                "tax": (item.get("tax", 0) or 0) / 100.0,
                "net_amount": (item.get("amount", 0) or 0) / 100.0 - (item.get("fees", 0) or 0) / 100.0,
                "settlement_date": pd.to_datetime(item.get("created_at", 0), unit="s", errors="coerce"),
                "status": item.get("status", "unknown"),
                "utr": item.get("utr", ""),
            }
        )
    return pd.DataFrame(rows)


def verify_webhook_signature(payload_body: bytes, received_signature: str) -> bool:
    """
    Verify the `X-Razorpay-Signature` header per Razorpay's webhook spec:
    https://razorpay.com/docs/webhooks/validate-test/

    This uses a constant-time comparison (hmac.compare_digest) to avoid
    timing side-channel attacks, and MUST be called on the raw request body
    bytes — never on a re-serialized/parsed JSON object, since re-encoding
    can change byte-for-byte formatting and break signature verification.
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.error("razorpay_webhook_secret_missing")
        return False
    expected_signature = hmac.new(
        key=settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, received_signature or "")
