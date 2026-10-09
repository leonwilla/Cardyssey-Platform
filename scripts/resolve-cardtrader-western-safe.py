#!/usr/bin/env python3
"""Exact English western leftovers; preview by default, explicit --apply to write.

CardTrader listings are asking prices. Require explicit English, Near Mint/Mint,
ungraded single cards and exact printing. Never infer NM from played listings.
History is inserted only for rows actually changed under the original identity.
"""
import argparse
import importlib.util
import json
import re
import statistics
import urllib.parse
import urllib.request
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

spec = importlib.util.spec_from_file_location("western_retail", Path(__file__).with_name("resolve-zhtw-retailer-prices.py"))
retail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retail)
BASE = "https://api.cardtrader.com/api/v2"
SET_CODE = {"bwp": "bwbsp", "tk-xy-b": "bisharp", "tk-xy-w": "wigglytuff", "mep": "mep"}
TCGCSV_GROUP = {"bwp": 1407, "tk-xy-b": 1533, "tk-xy-w": 1533, "mep": 24451}
SOURCES = {"CARDTRADER_MARKETPLACE", "TCGCSV_TCGPLAYER"}
NM_FACTOR = Decimal("0.92")


def norm(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def num(value):
    value = str(value or "").strip().lower().split("/", 1)[0].strip()
    return str(int(value)) if value.isdigit() else value


def eligible(row):
    v = row["variant"]
    return (row["language_code"] == "en" and row["set_id"] in SET_CODE
            and row["legacy_variant"] in ("NORMAL", "HOLO")
            and norm(v.get("type")) == {"NORMAL": "normal", "HOLO": "holo"}[row["legacy_variant"]]
            and v.get("id") == row["variant_id"] and v.get("legacyVariant") == row["legacy_variant"]
            and not any(v.get(k) for k in ("stamps", "subtype", "foil"))
            and str(v.get("size") or "standard").lower() == "standard")


def match_blueprint(row, blueprints, expansion_id):
    if not eligible(row):
        return None, "catalog_variant"
    candidates = []
    for b in blueprints:
        if b.get("game_id") != 5 or b.get("category_id") != 73 or b.get("expansion_id") != expansion_id:
            continue
        if num((b.get("fixed_properties") or {}).get("collector_number")) != num(row["local_id"]):
            continue
        if norm(b.get("name")) != norm(row["name"]):
            continue
        version = str(b.get("version") or "")
        # Fail closed on unlabelled, special or ambiguous editions.
        printing = "NORMAL" if re.match(r"^Non-Holo\s*\|", version, re.I) else (
            "HOLO" if re.match(r"^Holo(?: Promo)?\s*\|", version, re.I) else None)
        if printing != row["legacy_variant"] or re.search(
                r"reverse|oversized|jumbo|stamp|edition|staff|winner|signed|world|error", version, re.I):
            continue
        candidates.append(b)
    return (candidates[0], None) if len(candidates) == 1 else (None, "blueprint_missing_or_ambiguous")


def explicitly_false(value):
    return value is False or value == "false"


def listing_amount(product, blueprint_id):
    props = product.get("properties_hash") or {}
    if product.get("blueprint_id") != blueprint_id or not explicitly_false(product.get("graded")):
        return None
    if not all(explicitly_false(props.get(k)) for k in ("signed", "altered")):
        return None
    if str(props.get("pokemon_language") or "").lower() != "en":
        return None
    if props.get("condition") not in ("Near Mint", "Mint"):
        return None
    # The accepted blueprint has one explicit ordinary printing, no reverse option.
    if any("reverse" in str(k).lower() and not explicitly_false(v) for k, v in props.items()):
        return None
    if product.get("bundle_size") != 1 or type(product.get("quantity")) is not int or product["quantity"] <= 0:
        return None
    price = product.get("price") or {}
    cents = price.get("cents")
    if type(cents) is not int or cents <= 0 or price.get("currency") != "EUR":
        return None
    return Decimal(cents) / 100


def tcgcsv_amount(row, blueprint, prices, usd_eur):
    if usd_eur is None or blueprint.get("tcg_player_id") is None:
        return None
    expected = {"NORMAL": "normal", "HOLO": "holofoil"}[row["legacy_variant"]]
    matches = [p for p in prices if p.get("productId") == blueprint["tcg_player_id"]
               and norm(p.get("subTypeName")) == expected]
    if len(matches) != 1:
        return None
    # Mid/low asking quotes cannot silently replace the market price statistic.
    usd = retail.positive_decimal(matches[0].get("marketPrice"))
    return usd * usd_eur if usd is not None else None


def get_json(url, token=None):
    headers = {"Accept": "application/json", "User-Agent": "Cardyssey-western-exact/0.4"}
    if token:
        headers["Authorization"] = "Bearer " + token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as response:
        return json.load(response)


def load_targets():
    sql = """SELECT COALESCE(json_agg(x),'[]'::json)::text FROM (
    SELECT c.card_id,c.language_code,c.set_id,c.local_id,c.name,p.variant_id,p.legacy_variant,
           p.updated_at old_updated,c.image_source_url old_image,v.value variant
    FROM tcg_price_cache p JOIN catalog_cards_mirror c USING(card_id,language_code)
    CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
    WHERE p.language_code='en' AND p.resolution_status='NO_PRICE'
      AND c.set_id IN ('bwp','tk-xy-b','tk-xy-w','mep') AND v.value->>'id'=p.variant_id
    ORDER BY c.set_id,c.local_id,p.variant_id) x"""
    return json.loads(retail.db(sql))


def apply_updates(updates):
    if not updates:
        return {"prices": 0, "history": 0}
    keys = set()
    for u in updates:
        row = u["row"]
        key = (row["card_id"], row["variant_id"])
        if (not eligible(row) or u["source"] not in SOURCES or key in keys
                or retail.positive_decimal(u["base_eur"]) is None):
            raise ValueError("Invalid or duplicate exact western update")
        keys.add(key)
    return json.loads(retail.db(apply_sql(updates)))


def apply_sql(updates):
    payload = retail.quote(json.dumps(updates))
    return """WITH inputs AS (
      SELECT item->'row' r,item->>'source' source,item->>'base_eur' base,
             item->>'detail' detail FROM jsonb_array_elements(""" + payload + """::jsonb) item
    ), written AS (
      UPDATE tcg_price_cache p SET source=i.source,base_eur=i.base::numeric,updated_at=NOW(),
        resolution_status='PRICE_FOUND',failure_detail=i.detail,next_attempt_at=NOW()+INTERVAL '7 days'
      FROM inputs i JOIN catalog_cards_mirror c ON c.card_id=i.r->>'card_id' AND c.language_code='en'
      WHERE p.card_id=c.card_id AND p.language_code='en' AND p.variant_id=i.r->>'variant_id'
        AND p.resolution_status='NO_PRICE'
        AND p.updated_at IS NOT DISTINCT FROM (i.r->>'old_updated')::timestamptz
        AND c.set_id=i.r->>'set_id' AND c.local_id=i.r->>'local_id' AND c.name=i.r->>'name'
        AND c.image_source_url IS NOT DISTINCT FROM i.r->>'old_image'
        AND p.legacy_variant=i.r->>'legacy_variant'
        AND EXISTS(SELECT 1 FROM jsonb_array_elements(c.variants) v WHERE v=i.r->'variant')
      RETURNING p.card_id,p.language_code,p.variant_id,p.source,p.base_eur,p.updated_at
    ), history AS (
      INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at)
      SELECT card_id,language_code,variant_id,source,base_eur,updated_at FROM written RETURNING 1
    ) SELECT jsonb_build_object('prices',(SELECT COUNT(*) FROM written),'history',(SELECT COUNT(*) FROM history));"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    token = next((line.split("=", 1)[1].strip() for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines()
                  if line.startswith("CARDTRADER_API_TOKEN=")), "")
    if not token:
        raise SystemExit("CardTrader credentials unavailable")
    rows = load_targets()
    rejected = Counter()
    expansions = get_json(BASE + "/expansions", token)
    resolved = []
    for set_id in SET_CODE:
        targets = [r for r in rows if r["set_id"] == set_id]
        if not targets:
            continue
        es = [e for e in expansions if e.get("game_id") == 5 and str(e.get("code", "")).lower() == SET_CODE[set_id]]
        if len(es) != 1:
            rejected["expansion_missing_or_ambiguous"] += len(targets)
            continue
        eid = es[0]["id"]
        blueprints = get_json(BASE + "/blueprints/export?expansion_id=" + str(eid), token)
        for row in targets:
            b, reason = match_blueprint(row, blueprints, eid)
            if reason:
                rejected[reason] += 1
            else:
                resolved.append((row, b, eid))
    markets = {eid: get_json(BASE + "/marketplace/products?" + urllib.parse.urlencode({"expansion_id": eid}), token)
               for eid in sorted({eid for _, _, eid in resolved})}
    updates = []
    pending = []
    for row, b, eid in resolved:
        vals = [v for p in markets[eid].get(str(b["id"]), []) if (v := listing_amount(p, b["id"])) is not None]
        if vals:
            amount = statistics.median(sorted(vals)[:7])
            updates.append(dict(row=row, source="CARDTRADER_MARKETPLACE",
                                base_eur=str((amount / NM_FACTOR).quantize(Decimal(".0001"), rounding=ROUND_HALF_UP)),
                                detail=f"Exact English {row['legacy_variant']} blueprint {b['id']}; explicit NM/Mint; ASKING median lowest seven; eligible listings={len(vals)}"))
        else:
            pending.append((row, b))
    if pending:
        fx = retail.positive_decimal(get_json("https://api.frankfurter.dev/v2/rate/USD/EUR").get("rate"))
        groups = {g: get_json(f"https://tcgcsv.com/tcgplayer/3/{g}/prices").get("results", [])
                  for g in sorted({TCGCSV_GROUP[r["set_id"]] for r, b in pending if b.get("tcg_player_id") is not None})}
        for row, b in pending:
            amount = tcgcsv_amount(row, b, groups.get(TCGCSV_GROUP[row["set_id"]], []), fx)
            if amount is None:
                rejected["no_exact_price"] += 1
                continue
            updates.append(dict(row=row, source="TCGCSV_TCGPLAYER",
                                base_eur=str((amount / NM_FACTOR).quantize(Decimal(".0001"), rounding=ROUND_HALF_UP)),
                                detail=f"Exact English {row['legacy_variant']} TCGplayer product {b['tcg_player_id']}; blueprint {b['id']}; marketPrice USD; USD/EUR={fx}"))
    report = dict(candidates=len(rows), resolved=len(resolved), matched=len(updates), rejected=dict(rejected),
                  updates=updates, applied=apply_updates(updates) if args.apply else {"prices": 0, "history": 0})
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "updates"}))


if __name__ == "__main__":
    main()
