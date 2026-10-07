#!/usr/bin/env python3
"""Resolve safe Traditional-Chinese shared Cardmarket holo-family prices.

Only fills an unresolved HOLO/REVERSE target when the live TCGdex card has
exactly one holo-like physical variant, that variant is plain/standard, and
exactly one sibling Cardmarket product exposes a positive holo-family price.
Fails closed for all ambiguous/special printings.
"""
import argparse
import concurrent.futures
import math
import subprocess
import requests

LANG = "zh-tw"
BASE = f"https://api.tcgdex.net/v2/{LANG}/cards"
HOLO_KEYS = (
    "trend-holo",
    "avg1-holo",
    "avg7-holo",
    "avg30-holo",
    "avg-holo",
    "low-holo",
)

def db(sql: str) -> str:
    return subprocess.run(
        [
            "docker", "exec", "cardyssey-db", "psql",
            "-U", "cardyssey", "-d", "cardyssey",
            "-At", "-F", "\t", "-c", sql,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

def q(value: str) -> str:
    return value.replace("'", "''")

def positive(value):
    return (
        value
        if isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
        else None
    )

def holo_price(cardmarket):
    if not isinstance(cardmarket, dict):
        return None
    for key in HOLO_KEYS:
        value = positive(cardmarket.get(key))
        if value is not None:
            return key, float(value)
    return None

def is_holo_like(variant):
    typ = str(variant.get("type") or "").strip().lower()
    return typ in ("reverse", "holo") or bool(str(variant.get("foil") or "").strip())

def is_plain_standard(variant):
    stamps = variant.get("stamp") or []
    subtype = str(variant.get("subtype") or "").strip()
    foil = str(variant.get("foil") or "").strip()
    size = str(variant.get("size") or "").strip().lower()
    return not stamps and not subtype and not foil and size in ("", "standard")

raw = db(
    """SELECT p.card_id,p.variant_id,p.legacy_variant
       FROM tcg_price_cache p
       JOIN catalog_cards_mirror c
         ON c.card_id=p.card_id AND c.language_code=p.language_code
       WHERE p.language_code='zh-tw'
         AND p.resolution_status='NO_PRICE'
         AND p.legacy_variant IN ('HOLO','REVERSE')
         AND c.set_id !~ '^(A[0-9]|B[0-9]|P-A)'
       ORDER BY p.card_id,p.variant_id"""
)

targets = {}
for line in raw.splitlines():
    if not line:
        continue
    card_id, variant_id, legacy = line.split("\t")
    targets.setdefault(card_id, []).append((variant_id, legacy))

def fetch(card_id):
    try:
        response = requests.get(
            f"{BASE}/{card_id}",
            headers={"Accept": "application/json", "User-Agent": "Cardyssey price backfill"},
            timeout=20,
        )
        if response.status_code != 200:
            return card_id, None
        return card_id, response.json()
    except Exception:
        return card_id, None

cards = {}
card_ids = sorted(targets)
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
    for index, (card_id, payload) in enumerate(pool.map(fetch, card_ids), 1):
        cards[card_id] = payload
        if index % 250 == 0 or index == len(card_ids):
            print(f"fetched={index}/{len(card_ids)}", flush=True)

resolved = []
for card_id, wanted in targets.items():
    payload = cards.get(card_id) or {}
    detailed = payload.get("variants_detailed") or []
    by_id = {
        str(v.get("variantId") or ""): v
        for v in detailed
        if str(v.get("variantId") or "")
    }
    holo_like = [v for v in detailed if is_holo_like(v)]
    if len(holo_like) != 1:
        continue

    only = holo_like[0]
    only_id = str(only.get("variantId") or "")
    if not only_id or not is_plain_standard(only):
        continue

    direct = holo_price(((only.get("pricing") or {}).get("cardmarket")))
    if direct is not None:
        continue

    candidates = set()
    for sibling in detailed:
        if str(sibling.get("variantId") or "") == only_id:
            continue
        cardmarket = ((sibling.get("pricing") or {}).get("cardmarket"))
        priced = holo_price(cardmarket)
        if priced is None or not isinstance(cardmarket, dict):
            continue
        product_id = cardmarket.get("idProduct")
        if product_id is None:
            continue
        key, price = priced
        candidates.add((str(product_id), key, round(price, 6)))

    if len(candidates) != 1:
        continue

    product_id, price_key, price = next(iter(candidates))
    for variant_id, legacy in wanted:
        if variant_id != only_id or legacy.upper() not in ("HOLO", "REVERSE"):
            continue
        resolved.append(
            (card_id, variant_id, legacy.upper(), float(price), product_id, price_key)
        )

print(f"targets={sum(len(v) for v in targets.values())}", flush=True)
print(f"cards={len(card_ids)}", flush=True)
print(f"resolved={len(resolved)}", flush=True)

parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()

if not args.apply or not resolved:
    for row in resolved[:20]:
        print("sample", *row, flush=True)
    raise SystemExit(0)

sql = ["BEGIN;"]
for card_id, variant_id, legacy, price, product_id, price_key in resolved:
    detail = q(f"Shared Cardmarket holo family; product {product_id}; {price_key}")
    sql.append(
        f"""UPDATE tcg_price_cache SET
source='TCGDEX_SHARED_HOLO',
base_eur={price},
updated_at=NOW(),
resolution_status='PRICE_FOUND',
failure_detail='{detail}',
next_attempt_at=NOW()+INTERVAL '7 days'
WHERE card_id='{q(card_id)}'
  AND language_code='zh-tw'
  AND variant_id='{q(variant_id)}'
  AND resolution_status='NO_PRICE';"""
    )
    sql.append(
        f"""INSERT INTO tcg_price_history
(card_id,language_code,variant_id,source,base_eur,captured_at)
VALUES ('{q(card_id)}','zh-tw','{q(variant_id)}','TCGDEX_SHARED_HOLO',{price},NOW());"""
    )
sql.append("COMMIT;")

subprocess.run(
    [
        "docker", "exec", "-i", "cardyssey-db", "psql",
        "-v", "ON_ERROR_STOP=1", "-U", "cardyssey", "-d", "cardyssey",
    ],
    input="\n".join(sql),
    text=True,
    check=True,
    stdout=subprocess.DEVNULL,
)
print(f"applied={len(resolved)}", flush=True)
