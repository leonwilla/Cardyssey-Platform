#!/usr/bin/env python3
"""Exact zh-TW single-card retail offers; dry-run unless --apply is supplied.

These are in-stock asking prices, never completed sales. Do not infer foils,
editions, language or condition from a cheap price. Currency is verified per
shop and the existing cache's NM/base convention is preserved explicitly.
"""
import argparse
import concurrent.futures
import json
import re
import subprocess
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

NM_FACTOR = Decimal("0.92")
SOURCES = {
    "playersclubhk.com": {
        "source": "WEB_PLAYERSCLUB_HK",
        "collections": {
            "SC1a": "sc1a-劍-盾set-a", "SC1b": "sc1b-劍-盾set-b",
            "SC2a": "sc2a-無極力量-set-a", "SC2b": "sc2b-無極力量-set-b",
            "SC1D": "sc1d-v起始牌組-劍盾", "SC2D": "sc2d-劍盾-無極力量",
            "SCB": "scb", "SCD": "scd-寶可夢v起始牌組-強大",
            "SDM": "sdm-初階牌組-超夢",
        },
    },
    "beehivetcg.com": {
        "source": "WEB_BEEHIVE_HK",
        "collections": {
            "SC1a": "sc1a-劍-盾-set-a", "SC1b": "sc1b-劍-盾set-b",
            "SC2a": "sc2a-無極力量set-a", "SC2b": "sc2b-無極力量set-b",
            "SC1D": "sc1d-起始牌組劍-盾", "SC2D": "sc2d-起始牌組無極力量",
            "SCA": "sca-起始牌組搭檔", "SCB": "scb-起始牌組挑戰",
            "SCC": "scc-v起始牌組進化", "SCD": "scd-v起始牌組強大",
        },
    },
}
TITLE = re.compile(r"^([A-Za-z0-9]+)\s+(\d+)\s*/\s*(\d+)\s+(.+)$")
RARITY = re.compile(r"\s+(?:C|U|R|RR|RRR|SR|UR|HR|AR|SAR|ACE)$", re.I)


def normalize(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value))).casefold()


def positive_decimal(value):
    try:
        number = Decimal(str(value))
        return number if number.is_finite() and number > 0 else None
    except (InvalidOperation, ValueError):
        return None


def get_json(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "Cardyssey/0.3 public-price-audit", "Accept": "application/json",
    })
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def db(sql):
    result = subprocess.run(
        ["docker", "exec", "-i", "cardyssey-db", "psql", "-U", "cardyssey", "-d", "cardyssey",
         "-X", "-qAt", "-v", "ON_ERROR_STOP=1"],
        input="SET statement_timeout='20s';\n" + sql, text=True,
        capture_output=True, check=True, timeout=30,
    )
    return result.stdout.strip()


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def eligible_variant(row):
    variant = row["variant"]
    return (
        row["language_code"] == "zh-tw" and row["variant_count"] == 1
        and row["variant_id"] == "generated" and row["legacy_variant"] == "NORMAL"
        and variant.get("type") == "normal"
        and not any(variant.get(k) for k in ("foil", "stamps", "subtype"))
        and variant.get("size", "standard") in (None, "standard")
    )


def match_offer(row, product, host, collection_set):
    """Return (offer, rejection reason); a collection alone never proves identity."""
    if not eligible_variant(row):
        return None, "catalog_variant"
    title = unicodedata.normalize("NFKC", str(product.get("title", ""))).strip()
    match = TITLE.fullmatch(title)
    if not match:
        return None, "title"
    code, number, total, name = match.groups()
    if code.casefold() != collection_set.casefold() or code.casefold() != row["set_id"].casefold():
        return None, "set"
    if int(number) != int(row["local_id"]) or int(total) != row["official_count"]:
        return None, "number"
    if normalize(RARITY.sub("", name)) != normalize(row["name"]):
        return None, "name_or_printing"
    variants = product.get("variants", [])
    if len(variants) != 1 or variants[0].get("title") != "Default Title":
        return None, "retailer_variant"
    variant = variants[0]
    if host == "playersclubhk.com":
        if "Pokémon TCG  (Chinese)" not in product.get("tags", []):
            return None, "language"
    elif host == "beehivetcg.com":
        sku = str(variant.get("sku", "")).lower()
        prefixed = sku.startswith("pkmcn" + code.lower() + "-")
        # Older deck products use SCC-001 instead of pkmcnscc-001. Require
        # the Chinese product category AND the exact numeric SKU in that case.
        legacy = product.get("product_type") == "PKMCN" and re.fullmatch(
            re.escape(code.lower()) + r"-0*" + str(int(number)), sku,
        )
        if not (prefixed or legacy):
            return None, "language"
    else:
        return None, "source"
    if variant.get("available") is not True:
        return None, "sold_out"
    price = positive_decimal(variant.get("price"))
    if price is None:
        return None, "price"
    handle = product.get("handle")
    if not isinstance(handle, str) or not handle or not product.get("id"):
        return None, "product_identity"
    return {
        "source": SOURCES[host]["source"], "hkd": str(price), "title": title,
        "url": "https://" + host + "/products/" + urllib.parse.quote(handle, safe=""),
        "product_id": product["id"], "offer_variant_id": variant.get("id"),
    }, None


def load_collection(task):
    host, code, handle = task
    products, seen = [], set()
    try:
        for page in range(1, 4):
            url = ("https://" + host + "/collections/" + urllib.parse.quote(handle, safe="")
                   + "/products.json?limit=250&page=" + str(page))
            data = get_json(url)
            batch = data["products"]
            if not isinstance(batch, list):
                raise ValueError("invalid product feed")
            for product in batch:
                if product.get("id") in seen:
                    raise ValueError("repeated product/pagination")
                seen.add(product.get("id"))
                products.append(product)
            if len(batch) < 250:
                return host, code, products, None
        return host, code, [], "pagination_limit"
    except Exception as error:
        return host, code, [], type(error).__name__ + ": " + str(error)


def load_targets():
    sources = ",".join(quote(v["source"]) for v in SOURCES.values())
    raw = db("""SELECT COALESCE(jsonb_agg(row_to_json(t)), '[]'::jsonb) FROM (
      SELECT p.card_id,p.language_code,p.variant_id,p.legacy_variant,p.resolution_status,
             p.source,p.updated_at,c.set_id,c.local_id,c.name,s.official_count,
             jsonb_array_length(c.variants) AS variant_count,v.value AS variant
      FROM tcg_price_cache p JOIN catalog_cards_mirror c USING(card_id,language_code)
      JOIN catalog_sets_mirror s USING(set_id,language_code)
      CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
      WHERE p.language_code='zh-tw' AND p.variant_id=v.value->>'id'
        AND c.local_id ~ '^[0-9]+$' AND s.official_count>0
        AND (p.resolution_status IN ('NO_PRICE','NO_PUBLIC_PRICE')
             OR (p.source IN (""" + sources + """) AND
                 (TRUE)))
      ORDER BY c.set_id,c.local_id,p.variant_id
    ) t;""")
    return [row for row in json.loads(raw) if eligible_variant(row)]


def apply_updates(updates):
    if not updates:
        return 0
    values = []
    for update in updates:
        row, offer = update["row"], update["offer"]
        language = row.get("language_code", "zh-tw")
        if language not in ('de','en','ja','ko','zh-cn','zh-tw'):
            raise ValueError("unsupported price language")
        currency = offer.get("currency", "HKD")
        amount = offer.get("amount", offer.get("hkd"))
        if currency not in ('HKD','JPY','EUR') or positive_decimal(amount) is None or positive_decimal(update['base_eur']) is None:
            raise ValueError("invalid retail currency/price")
        detail = json.dumps({
            "basis": "ASKING", "currency": currency, "listed": amount,
            ("fx_hkd_eur" if currency == "HKD" else "fx_to_eur"): update["fx"], "fx_date": update["fx_date"],
            "observed_at": update["observed_at"], "in_stock": True,
            "nm_base_factor": str(NM_FACTOR), "title": offer["title"],
            "url": offer["url"], "product_id": offer["product_id"],
            "offer_variant_id": offer.get("offer_variant_id"),
            **({"condition": offer["condition"]} if offer.get("condition") else {}),
            **({"identity_method": offer["identity_method"], "blueprint_id": offer.get("blueprint_id")} if offer.get("identity_method") else {}),
        }, ensure_ascii=False, separators=(",", ":"))
        values.append("(" + ",".join(map(quote, (
            row["card_id"], language, row["variant_id"], offer["source"], update["base_eur"],
            detail, row["updated_at"], row["resolution_status"],
        ))) + ")")
    # Update + history are one statement. A concurrently refreshed row is skipped.
    sql = """WITH incoming(card_id,language_code,variant_id,source,base_eur,detail,old_updated,old_status) AS (
      VALUES """ + ",".join(values) + """
    ), changed AS (
      UPDATE tcg_price_cache p SET source=i.source,base_eur=i.base_eur::numeric,
        resolution_status='PRICE_FOUND',failure_detail=i.detail,updated_at=NOW(),
        next_attempt_at=NOW()+INTERVAL '7 days'
      FROM incoming i WHERE p.card_id=i.card_id AND p.variant_id=i.variant_id
        AND p.language_code=i.language_code AND p.resolution_status=i.old_status
        AND p.updated_at=i.old_updated::timestamptz
      RETURNING p.card_id,p.language_code,p.variant_id,p.source,p.base_eur
    ), recorded AS (
      INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at)
      SELECT card_id,language_code,variant_id,source,base_eur,NOW() FROM changed RETURNING 1
    ) SELECT COUNT(*) FROM recorded;"""
    return int(db(sql))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    rows = load_targets()
    report = {"candidates": len(rows), "errors": [], "rejected": {}, "updates": []}
    if not rows:
        print(json.dumps(report)); return
    fx_data = get_json("https://api.frankfurter.dev/v2/rate/HKD/EUR")
    fx = positive_decimal(fx_data.get("rate"))
    if fx is None or not fx_data.get("date"):
        raise SystemExit("HKD/EUR rate/date unavailable; no writes")
    by_set = defaultdict(list)
    for row in rows:
        by_set[row["set_id"].casefold()].append(row)
    tasks = []
    for host, source in SOURCES.items():
        try:
            if get_json("https://" + host + "/cart.js").get("currency") != "HKD":
                raise ValueError("unverified shop currency")
        except Exception as error:
            report["errors"].append({"host": host, "error": str(error)}); continue
        tasks.extend((host, code, handle) for code, handle in source["collections"].items()
                     if code.casefold() in by_set)
    offers = defaultdict(list)
    rejected = Counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for host, code, products, error in pool.map(load_collection, tasks):
            if error:
                report["errors"].append({"host": host, "set": code, "error": error}); continue
            index = defaultdict(list)
            for product in products:
                match = TITLE.fullmatch(unicodedata.normalize("NFKC", str(product.get("title", ""))).strip())
                if match:
                    index[int(match[2])].append(product)
            for row in by_set[code.casefold()]:
                for product in index[int(row["local_id"])]:
                    offer, reason = match_offer(row, product, host, code)
                    if offer:
                        offers[(row["card_id"], row["variant_id"])].append(offer)
                    else:
                        rejected[reason] += 1
            print(json.dumps({"host": host, "set": code, "products": len(products)}), flush=True)
    observed_at = datetime.now(timezone.utc).isoformat()
    for row in rows:
        matches = offers.get((row["card_id"], row["variant_id"]), [])
        if not matches:
            continue
        chosen = min(matches, key=lambda offer: Decimal(offer["hkd"]))
        base = (Decimal(chosen["hkd"]) * fx / NM_FACTOR).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        report["updates"].append({"row": row, "offer": chosen, "base_eur": str(base),
                                  "fx": str(fx), "fx_date": fx_data["date"], "observed_at": observed_at})
    report["rejected"] = dict(rejected)
    # Any provider error keeps this run read-only: no partial batch is called complete.
    report["applied"] = apply_updates(report["updates"]) if args.apply and not report["errors"] else 0
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"candidates": len(rows), "matched": len(report["updates"]),
                      "applied": report["applied"], "rejected": report["rejected"],
                      "errors": report["errors"]}, ensure_ascii=False), flush=True)
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
