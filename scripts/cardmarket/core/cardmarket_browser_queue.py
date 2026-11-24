"""Eligibility for the Cardmarket DE/EN browser queue and its monitoring."""

import json
import re
from decimal import Decimal, InvalidOperation


def browser_scan_tier(row, human_confirmed=False):
    """Match the live Windows collector's queue rules."""
    if str(row.get("needs_price") or "").upper() == "YES":
        return 0
    try:
        price = Decimal(str(row.get("existing_price_eur") or "0"))
    except InvalidOperation:
        price = Decimal(0)
    if price.is_finite() and price >= 20:
        return 1
    print_type = str(row.get("drucktyp") or "").strip().casefold()
    stamp = str(row.get("stempel") or "").strip().casefold()
    special = (
        bool(str(row.get("foil") or "").strip() or str(row.get("sonderdruck") or "").strip())
        or stamp not in ("", "[]", "null")
        or print_type not in ("", "normal", "nonholo", "common", "holo", "reverse")
    )
    if special and (human_confirmed or str(row.get("routing_state") or "").upper()
                    in ("VERIFIED_PRODUCT_ID", "HUMAN_CONFIRMED")):
        return 2
    if str(row.get("manual_scan_requested_at") or "").strip():
        return 3
    return 4


def human_confirmed_print_keys(base, language):
    path = base / "cardmarket-verified-print-mapping-cache.json"
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("schema") != 1 or data.get("source") != "CARDYSSEY_HUMAN_CONFIRMED_PRINT_ONLY":
        raise ValueError("Invalid Cardmarket verified print mapping cache")
    return {
        (row["card_id"], row["variant_id"])
        for row in data.get("confirmedMappings", [])
        if row.get("language_code") == language and row.get("mapping_status") == "HUMAN_CONFIRMED"
        and re.fullmatch(r"[0-9]{4,12}", str(row.get("product_id") or ""))
    }
