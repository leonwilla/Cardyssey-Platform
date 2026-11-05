#!/usr/bin/env python3
"""Refresh unresolved Cardyssey prices from CardTrader's official marketplace API.

No scraping is used. The job is optional and exits successfully when no
CARDTRADER_API_TOKEN is configured.

Identity chain (fail closed):
Cardyssey card -> exact TCGdex Cardmarket product id -> CardTrader blueprint
via blueprint.card_market_ids -> language/foil/condition filtered listings.

Only plain NORMAL/HOLO/REVERSE variants are eligible. Stamped, subtype and
special-foil variants are deliberately skipped unless they receive a dedicated
verified mapping elsewhere.
"""
import argparse
import concurrent.futures
import json
import math
import os
import re
import statistics
import subprocess
import time
import urllib.parse
import urllib.request
from market_condition_policy import classify_condition

parser=argparse.ArgumentParser()
parser.add_argument('--language',choices=('de','en','ja','ko','zh-cn','zh-tw'),default=None,
                    help='Process only one language; use de for this conservative rollout')
args=parser.parse_args()

BASE = "https://api.cardtrader.com/api/v2"
TCGDEX = "https://api.tcgdex.net/v2"
UA = "Cardyssey/0.4 cardtrader-price-refresh"
NM_FACTOR = 0.92


def db(sql):
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


def q(value):
    return str(value).replace("'", "''")


def token_from_env():
    token = os.getenv("CARDTRADER_API_TOKEN", "").strip()
    if token:
        return token
    path = "/home/tv/cardshop/platform/.env"
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("CARDTRADER_API_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


TOKEN = token_from_env()
if not TOKEN:
    print("cardtrader_disabled=no_token")
    raise SystemExit(0)


def get_json(url, auth=True, timeout=30):
    headers = {"Accept": "application/json", "User-Agent": UA}
    if auth:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def normalize_number(raw):
    value = str(raw or "").strip().lower()
    return re.sub(r"^0+(?=\d)", "", value)


def positive(value):
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def tcgdex_cardmarket_id(card_id, language):
    try:
        data = get_json(
            f"{TCGDEX}/{urllib.parse.quote(language)}/cards/"
            f"{urllib.parse.quote(card_id)}",
            auth=False,
            timeout=15,
        )
    except Exception:
        return None
    pricing = (data.get("pricing") or {}).get("cardmarket") or {}
    value = pricing.get("idProduct")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def load_targets():
    raw = db(
        """
SELECT p.card_id,p.language_code,p.variant_id,p.legacy_variant,
       c.local_id,c.name,c.variants::text,p.source,p.failure_detail
FROM tcg_price_cache p
JOIN catalog_cards_mirror c
  ON c.card_id=p.card_id AND c.language_code=p.language_code
WHERE p.language_code IN ('de','en','ja','ko','zh-cn','zh-tw')
  AND (
    p.resolution_status='NO_PRICE'
    OR p.source='CARDTRADER_MARKETPLACE'
  )
ORDER BY p.language_code,p.card_id,p.variant_id
"""
    )
    targets = []
    for line in raw.splitlines():
        parts = line.split("\t", 8)
        if len(parts) != 9:
            continue
        (
            card_id, language, variant_id, legacy,
            local_id, name, variants_json, source, failure,
        ) = parts
        if args.language and language != args.language:
            continue
        variants = json.loads(variants_json or "[]")
        variant = next(
            (v for v in variants if str(v.get("id") or "") == variant_id),
            None,
        )
        if not variant:
            continue
        if (
            variant.get("stamps")
            or variant.get("subtype")
            or variant.get("foil")
            or str(variant.get("size") or "").lower() not in ("", "standard")
        ):
            continue
        if legacy not in ("NORMAL", "HOLO", "REVERSE"):
            continue
        targets.append(
            {
                "card_id": card_id,
                "language": language,
                "variant_id": variant_id,
                "legacy": legacy,
                "local_id": local_id,
                "name": name,
                "source": source,
                "failure": failure,
            }
        )
    return targets


targets = load_targets()
if not targets:
    print("cardtrader_targets=0")
    raise SystemExit(0)

stored_pattern = re.compile(
    r"CardTrader blueprint (\d+); Cardmarket product (\d+)"
)

needed_cardmarket = set()
for row in targets:
    match = stored_pattern.search(row["failure"] or "")
    if match:
        # Re-resolve the blueprint weekly so we also recover its expansion id
        # for batched marketplace calls.
        row["blueprint_id"] = None
        row["expansion_id"] = None
        row["cardmarket_id"] = int(match.group(2))
    else:
        row["blueprint_id"] = None
        row["expansion_id"] = None
        row["cardmarket_id"] = None

missing_identity = [
    row for row in targets
    if row["cardmarket_id"] is None
]


def resolve_identity(row):
    product_id = tcgdex_cardmarket_id(
        row["card_id"],
        row["language"],
    )
    return row, product_id


with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    for row, product_id in pool.map(resolve_identity, missing_identity):
        if product_id:
            row["cardmarket_id"] = product_id

for row in targets:
    if row["cardmarket_id"] is not None and row["blueprint_id"] is None:
        needed_cardmarket.add(row["cardmarket_id"])

# Build only the Cardmarket-id -> CardTrader-blueprint identities needed today.
blueprint_by_cardmarket = {}
if needed_cardmarket:
    expansions = [
        x for x in get_json(f"{BASE}/expansions")
        if int(x.get("game_id") or 0) == 5
    ]

    for index, expansion in enumerate(expansions, 1):
        if not needed_cardmarket:
            break
        expansion_id = int(expansion["id"])
        try:
            blueprints = get_json(
                f"{BASE}/blueprints/export?expansion_id={expansion_id}",
                timeout=45,
            )
        except Exception:
            continue
        for blueprint in blueprints:
            ids = blueprint.get("card_market_ids")
            if ids is None:
                single = blueprint.get("card_market_id")
                ids = [] if single is None else [single]
            normalized_ids = set()
            for value in ids or []:
                try:
                    normalized_ids.add(int(value))
                except (TypeError, ValueError):
                    pass
            for product_id in needed_cardmarket & normalized_ids:
                blueprint_by_cardmarket.setdefault(product_id, []).append(
                    (
                        int(blueprint["id"]),
                        int(blueprint.get("expansion_id") or expansion_id),
                    )
                )
        remaining = needed_cardmarket - set(blueprint_by_cardmarket)
        if index % 25 == 0:
            print(
                f"cardtrader_blueprint_scan={index}/{len(expansions)} "
                f"remaining={len(remaining)}",
                flush=True,
            )
        if not remaining:
            break
        time.sleep(0.06)

for row in targets:
    if row["blueprint_id"] is not None:
        continue
    product_id = row["cardmarket_id"]
    candidates = blueprint_by_cardmarket.get(product_id, [])
    if len(candidates) == 1:
        row["blueprint_id"], row["expansion_id"] = candidates[0]


def cardtrader_language(language):
    return {
        "de": "de",
        "en": "en",
        "ja": "jp",
        "ko": "kr",
        "zh-cn": "zh-CN",
        "zh-tw": "zh-TW",
    }.get(language)


def listing_matches(row, product):
    if product.get("graded"):
        return False

    properties = product.get("properties_hash") or {}
    condition = str(properties.get("condition") or "").strip().lower()
    # Only DE: absent condition defaults to an *assumed* NM quote.
    # Explicit poorer grades and unfamiliar condition labels never qualify.
    if classify_condition(condition,language=row["language"]) not in ("explicit_nm", "assumed_nm"):
        return False

    expected_language = cardtrader_language(row["language"])
    if expected_language is None:
        return False

    language = str(
        properties.get("pokemon_language")
        or properties.get("language")
        or ""
    ).strip().lower()
    if language and language != expected_language.lower():
        return False

    reverse_value = None
    for key, value in properties.items():
        if "reverse" in str(key).lower():
            reverse_value = value
            break

    if row["legacy"] == "REVERSE":
        if str(reverse_value).lower() not in ("true", "1", "yes"):
            return False
    elif str(reverse_value).lower() in ("true", "1", "yes"):
        return False

    return True


def foil_filter(row):
    if row["legacy"] == "NORMAL":
        return "false"
    if row["legacy"] in ("HOLO", "REVERSE"):
        return "true"
    return None


def price_from_products(row, products):
    values = []
    condition_assumptions = 0
    for product in products:
        if not listing_matches(row, product):
            continue
        price = product.get("price") or {}
        cents = price.get("cents")
        currency = str(price.get("currency") or "").upper()
        if not isinstance(cents, (int, float)) or cents <= 0:
            continue
        if currency != "EUR":
            continue
        bundle = product.get("bundle_size") or 1
        try:
            unit = float(cents) / 100.0 / max(1, int(bundle))
        except (TypeError, ValueError):
            continue
        if positive(unit):
            values.append(unit)
            if classify_condition((product.get("properties_hash") or {}).get("condition"),language=row["language"]) == "assumed_nm":
                condition_assumptions += 1

    if not values:
        return None

    values.sort()
    sample = values[: min(7, len(values))]
    return round(statistics.median(sample), 4), len(values), condition_assumptions


# One marketplace call can return all blueprints of an expansion. Grouping here
# keeps the weekly refresh fast even when thousands of Asian cards are due.
market_groups = {}
for row in targets:
    if (
        row["blueprint_id"] is None
        or row["expansion_id"] is None
        or row["cardmarket_id"] is None
    ):
        continue

    provider_language = cardtrader_language(row["language"])
    foil = foil_filter(row)
    if provider_language is None or foil is None:
        continue

    key = (row["expansion_id"], provider_language, foil)
    market_groups.setdefault(key, []).append(row)

updates = []
for index, (key, rows) in enumerate(sorted(market_groups.items()), 1):
    expansion_id, provider_language, foil = key
    params = {
        "expansion_id": str(expansion_id),
        "language": provider_language,
        "foil": foil,
    }
    url = f"{BASE}/marketplace/products?" + urllib.parse.urlencode(params)

    try:
        payload = get_json(url, timeout=45)
    except Exception:
        payload = {}

    if isinstance(payload, dict):
        for row in rows:
            products = payload.get(str(row["blueprint_id"]), [])
            result = price_from_products(row, products)
            if result is None:
                continue
            listing_eur, sample_count, assumed_count = result
            base_eur = round(listing_eur / NM_FACTOR, 4)
            updates.append((row, base_eur, listing_eur, sample_count, assumed_count))

    if index % 25 == 0:
        print(
            f"cardtrader_market_groups={index}/{len(market_groups)} "
            f"updates={len(updates)}",
            flush=True,
        )

    # Marketplace documentation recommends at most one call per second.
    time.sleep(1.05)

print(
    f"cardtrader_targets={len(targets)} "
    f"identity_resolved={sum(1 for x in targets if x['blueprint_id'] is not None)} "
    f"price_updates={len(updates)}",
    flush=True,
)

if not updates:
    raise SystemExit(0)

sql = ["BEGIN;"]
for row, base_eur, listing_eur, sample_count, assumed_count in updates:
    detail = (
        f"CardTrader blueprint {row['blueprint_id']}; "
        f"Cardmarket product {row['cardmarket_id']}; "
        f"median cheapest NM EUR {listing_eur:.4f}; "
        f"listings {sample_count}; condition assumed NM for {assumed_count} listings"
    )
    sql.append(
        f"""
UPDATE tcg_price_cache
SET source='CARDTRADER_MARKETPLACE',
    base_eur={base_eur:.4f},
    updated_at=NOW(),
    resolution_status='PRICE_FOUND',
    failure_detail='{q(detail)}',
    next_attempt_at=NOW()+INTERVAL '7 days'
WHERE card_id='{q(row["card_id"])}'
  AND language_code='{q(row["language"])}'
  AND variant_id='{q(row["variant_id"])}';
"""
    )
    sql.append(
        f"""
INSERT INTO tcg_price_history
(card_id,language_code,variant_id,source,base_eur,captured_at)
VALUES (
  '{q(row["card_id"])}','{q(row["language"])}','{q(row["variant_id"])}',
  'CARDTRADER_MARKETPLACE',{base_eur:.4f},NOW()
);
"""
    )
sql.append("COMMIT;")

subprocess.run(
    [
        "docker", "exec", "-i", "cardyssey-db", "psql",
        "-v", "ON_ERROR_STOP=1",
        "-U", "cardyssey", "-d", "cardyssey", "-q",
    ],
    input="\n".join(sql),
    text=True,
    check=True,
)

for row, base_eur, listing_eur, sample_count, assumed_count in updates:
    print(
        f"{row['language']} {row['card_id']} {row['variant_id']} "
        f"base={base_eur:.4f} EUR listing={listing_eur:.4f} "
        f"blueprint={row['blueprint_id']} listings={sample_count}",
        flush=True,
    )
print(f"cardtrader_applied={len(updates)}", flush=True)
