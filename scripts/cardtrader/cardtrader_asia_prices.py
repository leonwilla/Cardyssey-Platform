#!/usr/bin/env python3
"""Japanese, Korean and Chinese card prices from CardTrader's official API.

No browser, no scraping: CardTrader (European marketplace, prices in EUR)
lists Japanese sets under the same codes as our catalog (sv9 = Battle
Partners, sm10 = Double Blaze) and keeps Korean and Chinese copies of the
same set in the same expansion (listing property pokemon_language).
Poke Ball / Master Ball reverse prints are separate expansions (p-sv8a,
m-sv8a, ...).

Per variant: listings of the exact card number in that language, Near Mint
or Mint, not graded/signed/altered, matching reverse and 1st-edition flags.
Price = median of the up to five cheapest offers (same rule as the
Cardmarket browser scan), at least two offers. Ambiguous cases (two
blueprints with one number, holo and non-holo of one card that CardTrader
does not separate, stamps) get no price.

  --dry-run            compute and report, write nothing
  --language ja        only one language (default: ja ko zh-tw zh-cn)
"""
import argparse
import json
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://api.cardtrader.com/api/v2"
ENV = Path("/home/tv/cardshop/platform/.env")
LANG = {"ja": "jp", "ko": "kr", "zh-tw": "zh-TW", "zh-cn": "zh-CN"}
SOURCE = {"ja": "CARDTRADER_JP_NM", "ko": "CARDTRADER_KO_NM", "zh-tw": "CARDTRADER_TW_NM", "zh-cn": "CARDTRADER_CN_NM"}
GOOD = {"Mint", "Near Mint"}
MIN_OFFERS = 2
# Our set code -> CardTrader expansion code where they differ. Each one was
# checked by hand (26.11.2026) on five cards per set (Japanese name vs.
# CardTrader name at the same number). neo4, PMCG1, PMCG6, SA and SMH do NOT
# match (other numbering) and stay unmapped.
ALIASES = {"smp": "sm-p", "sv-p": "promosv", "m-p": "mp-promo", "bwp": "bwpr", "xyp": "pxy", "vs1": "pvs",
           "sm4p": "sm4", "e1": "ec1", "pcg4": "gsso", "cp6": "ep20"}
FEW_OFFERS = 6        # below this many offers a price must be plausible ...
OUTLIER_FACTOR = 15   # ... i.e. at most 15x the median of its rarity in the set


def token():
    for line in ENV.read_text().splitlines():
        if line.startswith("CARDTRADER_API_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("CARDTRADER_API_TOKEN missing")


class Api:
    def __init__(self):
        self.tok, self.calls = token(), 0

    def get(self, path):
        for attempt in range(4):
            try:
                self.calls += 1
                req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + self.tok,
                                                                   "User-Agent": "Cardyssey/1.0 prices"})
                out = json.load(urllib.request.urlopen(req, timeout=90))
                time.sleep(0.4)
                return out
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise
        return None


def psql(sql, stdin=None):
    cmd = ["docker", "exec", "-i", "cardyssey-db", "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-U", "cardyssey",
           "-d", "cardyssey", "-At"] + (["-c", sql] if stdin is None else [])
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True, check=True).stdout


def lit(v):
    return "'" + str(v).replace("'", "''") + "'"


def number_key(value):
    """'109' -> ('', 109); '109/101' -> ('', 109); 'SV030' -> ('SV', 30)."""
    m = re.match(r"\s*([A-Za-z]*)0*([0-9]{1,4})", str(value or ""))
    return (m.group(1).upper(), int(m.group(2))) if m else None


def pattern_expansions(expansions):
    """code -> {'pokeball': exp, 'masterball': exp} for the separate pattern expansions."""
    by_code = {e["code"].lower(): e for e in expansions}
    by_name = {e["name"].lower(): e for e in expansions}
    out = {}
    for e in expansions:
        code, name = e["code"].lower(), e["name"]
        for prefix, kind in (("p-", "pokeball"), ("m-", "masterball")):
            if code.startswith(prefix) and code[2:] in by_code:
                out.setdefault(code[2:], {})[kind] = e
        m = re.match(r"(.+?)\s*-\s*(Master|Pok[eé]) ?Ball Reverse", name, re.I)
        if m and m.group(1).lower() in by_name:
            base = by_name[m.group(1).lower()]["code"].lower()
            out.setdefault(base, {}).setdefault("masterball" if m.group(2).lower() == "master" else "pokeball", e)
    return out


def variant_kind(v):
    """(kind, reverse, first_edition) or None when CardTrader cannot express it."""
    vtype = str(v.get("type") or "").lower()
    foil = str(v.get("foil") or "").lower().replace("é", "e")
    stamps = [str(s).lower() for s in (v.get("stamps") or [])]
    sub = str(v.get("subtype") or "").lower()
    first = any("1st" in s or "auflage" in s or "first" in s for s in stamps)
    if [s for s in stamps if not ("1st" in s or "auflage" in s or "first" in s)]:
        return None
    if sub not in ("", "unlimited"):
        return None
    if foil in ("pokeball", "masterball"):
        return foil, True, first
    if foil:
        return None
    if vtype == "reverse":
        return "main", True, first
    if vtype in ("normal", "holo"):
        return "main", False, first
    return None


def price_from(listings):
    prices = sorted(l["eur"] for l in listings)
    if len(prices) < MIN_OFFERS:
        return None
    return round(statistics.median(prices[:5]), 2)


def run(languages, dry_run):
    api = Api()
    expansions = [e for e in api.get("/expansions") if e.get("game_id") == 5]
    by_code = {e["code"].lower(): e for e in expansions}
    patterns = pattern_expansions(expansions)
    catalog = {}
    for line in psql("SELECT json_build_object('l',language_code,'c',card_id,'s',set_id,'n',local_id,'v',variants) "
                     "FROM catalog_cards_mirror WHERE language_code IN ('ja','ko','zh-tw','zh-cn')").splitlines():
        x = json.loads(line)
        if x["l"] in languages:
            catalog.setdefault(x["s"].lower(), []).append(x)
    stats = {l: {"variants": 0, "priced": 0, "no_expansion": 0, "ambiguous": 0, "no_offers": 0, "unsupported": 0}
             for l in languages}
    rows = {l: [] for l in languages}
    cache = {}

    def expansion_data(exp):
        if exp["id"] not in cache:
            blueprints = api.get(f"/blueprints/export?expansion_id={exp['id']}") or []
            products = api.get(f"/marketplace/products?expansion_id={exp['id']}") or {}
            numbers = {}
            for b in blueprints:
                key = number_key((b.get("fixed_properties") or {}).get("collector_number"))
                if key:
                    numbers.setdefault(key, []).append(b)
            cache[exp["id"]] = (numbers, products)
        return cache[exp["id"]]

    for code, cards in sorted(catalog.items()):
        for card in cards:
            lang = card["l"]
            # Aliases were checked for Japanese sets only (Korean promos are a
            # separate CardTrader expansion with other numbers).
            main = by_code.get(ALIASES.get(code, code) if lang == "ja" else code)
            variants = card["v"] or []
            kinds = {v["id"]: variant_kind(v) for v in variants}
            for v in variants:
                st = stats[lang]
                st["variants"] += 1
                kind = kinds[v["id"]]
                if kind is None:
                    st["unsupported"] += 1
                    continue
                k, reverse, first = kind
                # Holo and non-holo of one card share one CardTrader blueprint.
                same = [o for o in variants if o["id"] != v["id"] and kinds.get(o["id"]) == kind]
                if same:
                    st["ambiguous"] += 1
                    continue
                exp = main if k == "main" else (patterns.get(code) or {}).get(k)
                if not exp:
                    st["no_expansion"] += 1
                    continue
                numbers, products = expansion_data(exp)
                bps = numbers.get(number_key(card["n"])) or []
                if len(bps) != 1:
                    st["ambiguous" if bps else "no_offers"] += 1
                    continue
                bp = bps[0]
                offers = []
                for p in products.get(str(bp["id"]), []) or []:
                    ph = p.get("properties_hash") or {}
                    price = p.get("price") or {}
                    if (ph.get("pokemon_language") != LANG[lang] or ph.get("condition") not in GOOD
                            or p.get("graded") or ph.get("signed") or ph.get("altered")
                            or price.get("currency") != "EUR"):
                        continue
                    if k == "main" and bool(ph.get("pokemon_reverse")) != reverse:
                        continue
                    if "first_edition" in ph and bool(ph.get("first_edition")) != first:
                        continue
                    offers.append({"eur": price["cents"] / 100})
                value = price_from(offers)
                if value is None:
                    st["no_offers"] += 1
                    continue
                st["priced"] += 1
                rows[lang].append({"card": card["c"], "variant": v["id"], "price": value, "n": len(offers),
                                   "_ref": (exp["id"], (bp.get("fixed_properties") or {}).get("pokemon_rarity"), k),
                                   "detail": f"CardTrader {exp['code']} #{bp['id']} {bp['name']}: Median der "
                                             f"{min(5, len(offers))} günstigsten von {len(offers)} NM-Angeboten"})
    # Placeholder offers (e.g. 4,999 EUR for a common): with few offers a
    # price far above the usual price of the same rarity in the same set is
    # not a market price.
    for lang, items in rows.items():
        groups, rarity = {}, {}
        for r in items:
            groups.setdefault(r["_ref"], []).append(r["price"])
            rarity.setdefault((r["_ref"][1], r["_ref"][2]), []).append(r["price"])
        kept = []
        for r in items:
            usual = statistics.median(groups[r["_ref"]])
            overall = statistics.median(rarity[(r["_ref"][1], r["_ref"][2])])
            in_set = len(groups[r["_ref"]]) >= 3 and r["price"] > OUTLIER_FACTOR * usual
            # A whole set of placeholders (all ~5,000 EUR) is only visible
            # against the same rarity in all other sets.
            across = r["price"] > max(100, 100 * overall)
            if r["n"] < FEW_OFFERS and (in_set or across):
                stats[lang]["priced"] -= 1
                stats[lang]["implausible"] = stats[lang].get("implausible", 0) + 1
                continue
            r.pop("_ref")
            kept.append(r)
        rows[lang] = kept
    if not dry_run:
        for lang, items in rows.items():
            for i in range(0, len(items), 400):
                psql(None, stdin="BEGIN;\n" + SAVE.format(payload=lit(json.dumps(items[i:i + 400], ensure_ascii=False)),
                                                           lang=lit(lang), source=lit(SOURCE[lang])) + "\nCOMMIT;")
    return {"apiCalls": api.calls, **stats}


SAVE = """
WITH x AS (SELECT * FROM jsonb_to_recordset({payload}::jsonb) AS x(card text, variant text, price numeric, n int, detail text)),
legacy AS (
  SELECT x.*, COALESCE(t.legacy_variant, v.value->>'legacyVariant', 'NORMAL') AS legacy_variant
  FROM x LEFT JOIN tcg_price_cache t ON t.language_code={lang} AND t.card_id=x.card AND t.variant_id=x.variant
  LEFT JOIN catalog_cards_mirror c ON c.language_code={lang} AND c.card_id=x.card
  LEFT JOIN LATERAL (SELECT value FROM jsonb_array_elements(c.variants) value WHERE value->>'id'=x.variant LIMIT 1) v ON TRUE)
INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,source,base_eur,resolution_status,
  failure_detail,updated_at)
SELECT card,{lang},variant,legacy_variant,{source},price,'PRICE_FOUND',detail,NOW() FROM legacy
ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET source=EXCLUDED.source, base_eur=EXCLUDED.base_eur,
  resolution_status='PRICE_FOUND', failure_detail=EXCLUDED.failure_detail, updated_at=NOW()
WHERE NOT (upper(COALESCE(tcg_price_cache.source,'')) LIKE 'MANUAL%' OR upper(COALESCE(tcg_price_cache.source,'')) LIKE 'ADMIN%');
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--language", action="append", choices=sorted(LANG))
    a = p.parse_args()
    print(json.dumps(run(a.language or ["ja", "ko", "zh-tw", "zh-cn"], a.dry_run)))


if __name__ == "__main__":
    main()
