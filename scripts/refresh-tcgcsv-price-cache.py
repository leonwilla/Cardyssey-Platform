#!/usr/bin/env python3
"""Refresh already-verified TCGCSV/TCGplayer cache rows."""
import argparse
import json
import math
import re
import subprocess
import time
import urllib.request

UA = {"User-Agent": "Cardyssey/0.3 recurring-price-refresh", "Accept": "application/json"}
NEAR_MINT_FACTOR = 0.92

ALIASES = {
    "basep": 1418, "dpp": 1421, "mep": 24451, "svp": 22872,
    "swshp": 2545, "smp": 1861, "xyp": 1451, "bwp": 1407, "hsp": 1453,
    "sma": 2594, "dp1": 1430, "ex1": 1393, "ex3": 1376, "ex7": 1428, "exu": 1398,
    "np": 1423, "xya": 1938, "bog": 1455, "miscp": 2374, "tk-hs-g": 1540,
    "tk-xy-latio": 1536, "tk-xy-w": 1533, "tk-xy-n": 1532,
    "tk-xy-su": 1796,
}

def db(sql):
    return subprocess.run(
        ["docker", "exec", "cardyssey-db", "psql", "-U", "cardyssey",
         "-d", "cardyssey", "-At", "-F", "\t", "-c", sql],
        check=True, capture_output=True, text=True,
    ).stdout.strip()

def fetch_json(url, attempts=2):
    last = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.load(response)
        except Exception as error:
            last = error
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url}: {last}")

def norm(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

def set_key(name):
    value = str(name or "").lower()
    value = re.sub(r"^(ex|sm|xy)\s*[-:]\s*", "", value)
    value = re.sub(r"^swsh\d*\s*[:\-]\s*", "", value)
    value = re.sub(r"^sv\d*(?:\.\d+)?\s*[:\-]\s*", "", value)
    value = re.sub(r"^me\d*\s*[:\-]\s*", "", value)
    value = value.replace("base set", "")
    return norm(value)

def positive(value):
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0

def q(value):
    return str(value).replace("'", "''")

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()

rate_payload = fetch_json("https://api.frankfurter.dev/v2/rate/USD/EUR")
usd_to_eur = rate_payload.get("rate")
if not positive(usd_to_eur):
    raise SystemExit("USD/EUR rate unavailable")

raw = db("""
SELECT p.card_id,p.language_code,p.variant_id,p.failure_detail,
       c.set_id,COALESCE(es.name,s.name,'')
FROM tcg_price_cache p
JOIN catalog_cards_mirror c
  ON c.card_id=p.card_id AND c.language_code=p.language_code
LEFT JOIN catalog_sets_mirror es
  ON es.set_id=c.set_id AND es.language_code='en'
LEFT JOIN catalog_sets_mirror s
  ON s.set_id=c.set_id AND s.language_code=c.language_code
WHERE p.source='TCGCSV_TCGPLAYER'
  AND p.resolution_status='PRICE_FOUND'
  AND p.base_eur IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM price_source_routing routing
    WHERE routing.language_code=p.language_code AND routing.card_id=p.card_id
      AND routing.variant_id=p.variant_id
      AND routing.verification_state='VERIFIED_PRODUCT_ID'
      AND routing.primary_provider<>'TCGCSV_TCGPLAYER'
  )
ORDER BY p.language_code,c.set_id,p.card_id,p.variant_id
""")

rows = []
detail_re = re.compile(
    r"^TCGplayer product (\d+);\s*([^;]+?)(?:;\s*group\s+(\d+))?$",
    re.I,
)
for line in raw.splitlines():
    parts = line.split("\t", 5)
    if len(parts) != 6:
        continue
    card_id, language, variant_id, detail, set_id, set_name = parts
    match = detail_re.match(detail or "")
    if not match:
        continue
    rows.append({
        "card_id": card_id,
        "language": language,
        "variant_id": variant_id,
        "product_id": int(match.group(1)),
        "subtype": match.group(2).strip(),
        "group_id": int(match.group(3)) if match.group(3) else None,
        "set_id": set_id,
        "set_name": set_name,
    })

groups = fetch_json("https://tcgcsv.com/tcgplayer/3/groups").get("results") or []
by_key = {}
for group in groups:
    by_key.setdefault(set_key(group.get("name")), []).append(group)

set_to_gid = {}
unmapped = {}
for row in rows:
    sid = row["set_id"]
    if sid in set_to_gid or sid in unmapped:
        continue
    if sid in ALIASES:
        set_to_gid[sid] = ALIASES[sid]
        continue
    key = set_key(row["set_name"])
    candidates = by_key.get(key, [])
    if len(candidates) == 1:
        set_to_gid[sid] = int(candidates[0]["groupId"])
        continue
    matches = [
        group for group in groups
        if key
        and (key in set_key(group.get("name")) or set_key(group.get("name")) in key)
        and len(set_key(group.get("name"))) >= 4
    ]
    unique = {int(group["groupId"]): group for group in matches}
    if len(unique) == 1:
        set_to_gid[sid] = next(iter(unique))
    else:
        unmapped[sid] = row["set_name"]

by_group = {}
for row in rows:
    gid = row.get("group_id") or set_to_gid.get(row["set_id"])
    if gid is not None:
        by_group.setdefault(gid, []).append(row)

updates = []
feed_failures = []
for index, (gid, items) in enumerate(sorted(by_group.items()), 1):
    try:
        prices = fetch_json(
            f"https://tcgcsv.com/tcgplayer/3/{gid}/prices"
        ).get("results") or []
    except Exception as error:
        feed_failures.append((gid, str(error)))
        continue

    price_by_product = {}
    for entry in prices:
        try:
            pid = int(entry.get("productId") or 0)
        except (TypeError, ValueError):
            continue
        price_by_product.setdefault(pid, []).append(entry)

    for item in items:
        candidates = price_by_product.get(item["product_id"], [])
        expected_subtype = norm(item["subtype"])
        exact = [
            entry for entry in candidates
            if norm(entry.get("subTypeName")) == expected_subtype
        ]
        if len(exact) != 1:
            continue
        entry = exact[0]
        usd = entry.get("marketPrice")
        if not positive(usd):
            usd = entry.get("midPrice")
        if not positive(usd):
            continue
        base_eur = (float(usd) * float(usd_to_eur)) / NEAR_MINT_FACTOR
        if not positive(base_eur):
            continue
        updates.append({**item, "base_eur": round(base_eur, 4)})

    print(
        f"group={index}/{len(by_group)} gid={gid} rows={len(items)} updates={len(updates)}",
        flush=True,
    )
    time.sleep(0.05)

print(
    f"rows={len(rows)} mapped_sets={len(set_to_gid)} "
    f"unmapped_sets={len(unmapped)} feed_failures={len(feed_failures)} "
    f"safe_updates={len(updates)} usd_eur={usd_to_eur}",
    flush=True,
)
for sid, name in sorted(unmapped.items()):
    print(f"unmapped_set={sid} name={name}", flush=True)
for gid, error in feed_failures:
    print(f"feed_failure={gid} error={error}", flush=True)

if args.dry_run:
    raise SystemExit(0)

if not updates:
    raise SystemExit("No safe TCGCSV updates; refusing empty refresh")

sql = ["BEGIN;"]
for item in updates:
    sql.append(f"""
UPDATE tcg_price_cache
SET base_eur={item['base_eur']:.4f},
    updated_at=NOW(),
    failure_detail='TCGplayer product {item['product_id']}; {q(item['subtype'])}' ||
    CASE
      WHEN {str(item.get('group_id') is not None).upper()} THEN '; group {item.get('group_id') or 0}'
      ELSE ''
    END,
    next_attempt_at=NOW()+INTERVAL '168 hours'
WHERE card_id='{q(item['card_id'])}'
  AND language_code='{q(item['language'])}'
  AND variant_id='{q(item['variant_id'])}'
  AND source='TCGCSV_TCGPLAYER'
  AND resolution_status='PRICE_FOUND';
""")
    sql.append(f"""
INSERT INTO tcg_price_history
(card_id,language_code,variant_id,source,base_eur,captured_at)
VALUES (
  '{q(item['card_id'])}','{q(item['language'])}','{q(item['variant_id'])}',
  'TCGCSV_TCGPLAYER',{item['base_eur']:.4f},NOW()
);
""")
sql.append("COMMIT;")

subprocess.run(
    ["docker", "exec", "-i", "cardyssey-db", "psql",
     "-U", "cardyssey", "-d", "cardyssey", "-v", "ON_ERROR_STOP=1", "-q"],
    input="\n".join(sql), text=True, check=True,
)
print(f"applied={len(updates)}", flush=True)
