"""
Normalization Service for RazorRecon AI

Normalizes transaction data across sources while preserving original values.
All transformations are deterministic and reversible via stored originals.
"""

import re
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Optional
import pandas as pd
import numpy as np


# Date formats to try when parsing
DATE_FORMATS = [
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d %B %Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%d-%b-%Y",
]


def normalize_id(id_str: Optional[str]) -> str:
    """
    Normalize an ID string:
    - Strip whitespace
    - Convert to uppercase
    - Replace hyphens with underscores
    - Remove special chars except underscore
    """
    if id_str is None or (isinstance(id_str, float) and np.isnan(id_str)):
        return ""
    s = str(id_str).strip().upper()
    s = s.replace("-", "_")
    s = re.sub(r"[^A-Z0-9_]", "", s)
    return s


def normalize_amount(amount) -> float:
    """
    Normalize an amount to 2 decimal places using deterministic rounding.
    Removes currency symbols, commas, whitespace.
    """
    if amount is None or (isinstance(amount, float) and np.isnan(amount)):
        return 0.0
    if isinstance(amount, str):
        # Remove currency symbols and formatting
        cleaned = re.sub(r"[₹$€£,\s]", "", amount)
        try:
            amount = float(cleaned)
        except ValueError:
            return 0.0
    d = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(d)


def normalize_date(date_str: Optional[str]) -> str:
    """
    Parse a date string in various formats and return ISO 8601 (YYYY-MM-DD).
    Returns empty string if parsing fails.
    """
    if date_str is None or (isinstance(date_str, float) and np.isnan(date_str)):
        return ""
    date_str = str(date_str).strip()
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try pandas as fallback
    try:
        dt = pd.to_datetime(date_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str


def normalize_currency(currency: Optional[str]) -> str:
    """Normalize currency code to uppercase 3-letter code."""
    if currency is None or (isinstance(currency, float) and np.isnan(currency)):
        return "INR"
    c = str(currency).strip().upper()
    mapping = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP", "RUPEE": "INR", "RUPEES": "INR"}
    return mapping.get(c, c)


# Column mappings per source type, mapping expected column → normalized column name
SOURCE_COLUMNS = {
    "bank": {
        "id_col": "transaction_id",
        "payment_id_col": None,  # derived from transaction_id mapping
        "date_col": "transaction_date",
        "amount_col": "amount",
        "reference_col": "customer_reference",
        "currency_col": "currency",
    },
    "settlement": {
        "id_col": "settlement_id",
        "payment_id_col": "payment_id",
        "date_col": "settlement_date",
        "amount_col": "gross_amount",
        "reference_col": None,
        "currency_col": None,
    },
    "ledger": {
        "id_col": "ledger_id",
        "payment_id_col": "payment_id",
        "date_col": "transaction_date",
        "amount_col": "expected_amount",
        "reference_col": "customer_id",
        "currency_col": None,
    },
    "refund": {
        "id_col": "refund_id",
        "payment_id_col": "payment_id",
        "date_col": "refund_date",
        "amount_col": "refund_amount",
        "reference_col": None,
        "currency_col": None,
    },
    "chargeback": {
        "id_col": "chargeback_id",
        "payment_id_col": "payment_id",
        "date_col": "chargeback_date",
        "amount_col": "amount",
        "reference_col": None,
        "currency_col": None,
    },
}


def normalize_dataframe(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    """
    Normalize a DataFrame based on its source type.
    
    Preserves all original columns with 'original_' prefix.
    Adds normalized versions of key columns.
    
    Args:
        df: Input DataFrame
        source_type: One of 'bank', 'settlement', 'ledger', 'refund', 'chargeback'
    
    Returns:
        Normalized DataFrame with both original and normalized columns
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    result = df.copy()
    config = SOURCE_COLUMNS.get(source_type, {})
    
    # Preserve originals for all columns
    for col in result.columns:
        result[f"original_{col}"] = result[col]
    
    # Normalize the primary ID column
    id_col = config.get("id_col")
    if id_col and id_col in result.columns:
        result[id_col] = result[id_col].apply(normalize_id)
    
    # Normalize payment_id if present
    payment_id_col = config.get("payment_id_col")
    if payment_id_col and payment_id_col in result.columns:
        result[payment_id_col] = result[payment_id_col].apply(normalize_id)
    
    # Normalize date column
    date_col = config.get("date_col")
    if date_col and date_col in result.columns:
        result[date_col] = result[date_col].apply(normalize_date)
    
    # Normalize amount column
    amount_col = config.get("amount_col")
    if amount_col and amount_col in result.columns:
        result[amount_col] = result[amount_col].apply(normalize_amount)
    
    # Normalize other amount columns for settlements
    if source_type == "settlement":
        for col in ["fee", "tax", "net_amount", "gross_amount"]:
            if col in result.columns:
                result[col] = result[col].apply(normalize_amount)
    
    # Normalize recorded_amount for ledger
    if source_type == "ledger" and "recorded_amount" in result.columns:
        result["recorded_amount"] = result["recorded_amount"].apply(normalize_amount)
    
    # Normalize currency
    currency_col = config.get("currency_col")
    if currency_col and currency_col in result.columns:
        result[currency_col] = result[currency_col].apply(normalize_currency)
    
    # Normalize reference columns
    ref_col = config.get("reference_col")
    if ref_col and ref_col in result.columns:
        result[ref_col] = result[ref_col].apply(
            lambda x: str(x).strip().upper() if pd.notna(x) else ""
        )
    
    # Add source_type column
    result["_source_type"] = source_type
    
    return result


def create_payment_id_mapping(bank_df: pd.DataFrame) -> dict:
    """
    Create a mapping from bank transaction_id (BTX_XXXX) to payment_id (PAY_XXXX).
    This is a convention: BTX_0001 → PAY_0001
    """
    mapping = {}
    if "transaction_id" in bank_df.columns:
        for tx_id in bank_df["transaction_id"]:
            normalized = normalize_id(tx_id)
            # Extract number and create payment ID
            match = re.search(r"(\d+)", normalized)
            if match:
                num = match.group(1)
                mapping[normalized] = f"PAY_{num.zfill(4)}"
    return mapping
