"""Manual recovery filters: never touch a card that already has a positive price."""
import json
def filter_targets(rows, retail):
    priced=set(json.loads(retail.db("SELECT COALESCE(jsonb_agg(DISTINCT card_id),'[]') FROM tcg_price_cache WHERE base_eur>0;")))
    return [r for r in rows if r.get("old_status")!="PRICE_FOUND" and r["card_id"] not in priced]


MIN_NEW_CARDS = 1


def import_gate(updates, db, *, missing_only, errors=()):
    """Gate a complete manual batch; identity validation stays in each reader.

    Count distinct entirely unpriced cards, not quotations or variant rows.
    Weekly refreshes retain their previous behavior. Recheck all variants just
    before the writer; its transactional preservation guards still apply.
    """
    result = dict(required_new_cards=MIN_NEW_CARDS if missing_only else 0,
                  distinct_new_cards=0, duplicate_cards=0, existing_cards=0,
                  invalid_updates=0, allowed=False, reason=None)
    if errors:
        result["reason"] = "provider_errors"
        return result
    if not missing_only:
        result.update(allowed=True, reason="weekly_refresh")
        return result
    from decimal import Decimal, InvalidOperation
    ids = []
    for update in updates:
        row = update.get("row") or {}
        cid = row.get("card_id")
        try:
            amount = Decimal(str(update.get("base_eur")))
            valid = isinstance(cid, str) and bool(cid) and amount.is_finite() and amount > 0
        except (InvalidOperation, ValueError):
            valid = False
        if not valid:
            result["invalid_updates"] += 1
        else:
            ids.append(cid)
    priced = set(json.loads(db("SELECT COALESCE(jsonb_agg(DISTINCT card_id),'[]') FROM tcg_price_cache WHERE base_eur>0;")))
    priced.update(u["row"]["card_id"] for u in updates
                  if (u.get("row") or {}).get("old_status") == "PRICE_FOUND" and u["row"].get("card_id"))
    unique = set(ids)
    result.update(distinct_new_cards=len(unique - priced), duplicate_cards=len(ids)-len(unique),
                  existing_cards=len(unique & priced))
    for field, reason in (("invalid_updates", "invalid_updates"),
                          ("duplicate_cards", "duplicate_cards"),
                          ("existing_cards", "already_priced_cards")):
        if result[field]:
            result["reason"] = reason
            return result
    if result["distinct_new_cards"] < MIN_NEW_CARDS:
        result["reason"] = "below_minimum_new_cards"
        return result
    result.update(allowed=True, reason="minimum_new_cards_met")
    return result
