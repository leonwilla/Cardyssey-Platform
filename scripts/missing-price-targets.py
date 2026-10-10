"""Manual recovery filters: never touch a card that already has a positive price."""
import json
def filter_targets(rows, retail):
    priced=set(json.loads(retail.db("SELECT COALESCE(jsonb_agg(DISTINCT card_id),'[]') FROM tcg_price_cache WHERE base_eur>0;")))
    return [r for r in rows if r.get("old_status")!="PRICE_FOUND" and r["card_id"] not in priced]
