#!/usr/bin/env python3
"""Recover German TCG prices by exact Cardmarket product identity.

For remaining physical NO_PRICE rows, fetch current TCGdex details and only
reuse a card-level Cardmarket price when the selected physical variant points
at exactly that same Cardmarket product id. This is safe even when several
physical metadata variants share one Cardmarket listing: Cardmarket itself
prices them as one market bucket.
"""
import concurrent.futures
import json
import math
import subprocess
import requests

BASE = "https://api.tcgdex.net/v2/de/cards"

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def q(value):
    return value.replace("'","''")

def positive(value):
    return isinstance(value,(int,float)) and math.isfinite(value) and value > 0

def cardmarket_price(cm, variant):
    if not isinstance(cm,dict):
        return None
    typ = str(variant.get("type") or "").strip().lower()
    foil = str(variant.get("foil") or "").strip()
    holo_like = typ in ("holo","reverse") or bool(foil)
    keys = (
        ["trend-holo","avg1-holo","avg7-holo","avg30-holo","avg-holo","low-holo"]
        if holo_like else []
    ) + ["trend","avg1","avg7","avg30","avg","low"]
    for key in keys:
        value = cm.get(key)
        if positive(value):
            return float(value)
    return None

rows = db("""
SELECT p.card_id,p.variant_id,p.legacy_variant
FROM tcg_price_cache p
JOIN catalog_cards_mirror c
  ON c.card_id=p.card_id AND c.language_code=p.language_code
WHERE p.language_code='de'
  AND p.resolution_status='NO_PRICE'
  AND NOT (c.set_id ~ '^(A[0-9]|B[0-9])' OR c.set_id='P-A')
ORDER BY p.card_id,p.variant_id
""").splitlines()

targets = [tuple(line.split("\t")) for line in rows if line.strip()]
card_ids = sorted({row[0] for row in targets})
print(f"rows={len(targets)} cards={len(card_ids)}", flush=True)

def fetch(cid):
    for attempt in range(3):
        try:
            response = requests.get(
                f"{BASE}/{cid}",
                headers={"User-Agent":"Cardyssey price repair"},
                timeout=20,
            )
            if response.status_code == 200:
                return cid, response.json()
            if response.status_code == 404:
                return cid, None
        except requests.RequestException:
            pass
    return cid, None

cards = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    for index,(cid,payload) in enumerate(executor.map(fetch,card_ids),1):
        cards[cid] = payload
        if index % 250 == 0 or index == len(card_ids):
            print(f"fetched={index}", flush=True)

resolved = []
for cid,variant_id,legacy in targets:
    card = cards.get(cid)
    if not card:
        continue
    detailed = [
        item for item in (card.get("variants_detailed") or [])
        if not item.get("languages") or "de" in [str(x).lower() for x in item.get("languages") or []]
    ]
    selected = next(
        (item for item in detailed if str(item.get("variantId") or "") == variant_id),
        None,
    )
    if not selected:
        continue

    own_cm = ((selected.get("pricing") or {}).get("cardmarket") or {})
    own_price = cardmarket_price(own_cm, selected)
    if own_price is not None:
        resolved.append((cid,variant_id,legacy,own_price,"TCGDEX"))
        continue

    top_cm = ((card.get("pricing") or {}).get("cardmarket") or {})
    top_product = top_cm.get("idProduct")
    variant_product = (selected.get("thirdParty") or {}).get("cardmarket")
    if top_product is None or variant_product is None:
        continue
    if str(top_product) != str(variant_product):
        continue

    price = cardmarket_price(top_cm, selected)
    if price is not None:
        resolved.append((cid,variant_id,legacy,price,"TCGDEX_PRODUCT"))

print(f"resolved={len(resolved)}", flush=True)

sql = ["BEGIN;"]
for cid,variant_id,legacy,price,source in resolved:
    sql.append(f"""
UPDATE tcg_price_cache
SET source='{source}',
    base_eur={price},
    updated_at=NOW(),
    resolution_status='PRICE_FOUND',
    failure_detail=NULL,
    next_attempt_at=NOW()+INTERVAL '7 days'
WHERE language_code='de'
  AND card_id='{q(cid)}'
  AND variant_id='{q(variant_id)}';
""")
    sql.append(f"""
INSERT INTO tcg_price_history
(card_id,language_code,variant_id,source,base_eur,captured_at)
VALUES ('{q(cid)}','de','{q(variant_id)}','{source}',{price},NOW());
""")
sql.append("COMMIT;")

if resolved:
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],
        input="\n".join(sql), text=True, check=True, stdout=subprocess.DEVNULL
    )
print(f"applied={len(resolved)}", flush=True)
