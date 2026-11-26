#!/usr/bin/env python3
"""Reference values ("Richtwert") for card variants without any market price.

Shown in app and web as a clearly labelled reference, never counted in the
collection value (same mechanism as the older POKEMONTCGAPI_REFERENCE rows in
price_reference_candidates). Order (owner decision 26.11.2026, "every card
needs a value"):

1. Korean / Chinese card: price of the same card (same set, number, print)
   in Japanese - the identical card, other language edition.
2. Bulk cards (common / uncommon): median price of the same rarity and print
   in the same set and language (at least 5 priced cards), else the median of
   that rarity and print in the language (at least 20 priced cards).

Rare cards without a market price get no rarity median (a rare card's price
depends on the card); for them only rule 1 applies.

Rarity comes from our catalog, otherwise from CardTrader
(~/.local/state/cardtrader-asia-cards.json, written by
scripts/cardtrader/cardtrader_asia_prices.py).
"""
import argparse
import json
import statistics
import subprocess
from pathlib import Path

PROVIDER = "CARDYSSEY_REFERENCE"
CARD_INFO = Path.home() / ".local/state/cardtrader-asia-cards.json"
LANGS = ("de", "en", "ja", "ko", "zh-tw", "zh-cn")
BULK = {"common", "uncommon", "häufig", "ungewöhnlich", "c", "u", "コモン", "アンコモン", "일반", "언커먼", "普通", "非普通"}
SET_MIN, LANG_MIN = 5, 20


def psql(sql, stdin=None):
    cmd = ["docker", "exec", "-i", "cardyssey-db", "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-U", "cardyssey",
           "-d", "cardyssey", "-At"] + (["-c", sql] if stdin is None else [])
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True, check=True).stdout


def lit(v):
    return "'" + str(v).replace("'", "''") + "'"


def print_kind(v):
    t = str(v.get("type") or "").lower()
    foil = str(v.get("foil") or "").lower()
    stamps = [str(s).lower() for s in (v.get("stamps") or [])]
    if stamps or v.get("subtype") not in (None, "", "unlimited"):
        return None  # stamped / special prints: no generic reference
    return f"{t}|{foil}"


def load():
    info = {}
    try:
        info = json.loads(CARD_INFO.read_text())
    except (OSError, ValueError):
        pass
    cards = []
    sql = ("SELECT json_build_object('l',c.language_code,'c',c.card_id,'s',c.set_id,'n',c.local_id,'r',c.rarity,"
           "'v',c.variants) FROM catalog_cards_mirror c WHERE c.language_code IN ('de','en','ja','ko','zh-tw','zh-cn')")
    for line in psql(sql).splitlines():
        x = json.loads(line)
        ct = info.get(f"{x['l']}|{x['c']}") or {}
        rarity = (x["r"] or "").strip() or (ct.get("rarity") or "")
        cards.append({**x, "rarity": rarity})
    prices = {}
    for line in psql("SELECT language_code||'|'||card_id||'|'||variant_id||'|'||base_eur FROM tcg_price_cache "
                     "WHERE resolution_status='PRICE_FOUND' AND base_eur>0").splitlines():
        lang, card, variant, eur = line.split("|")
        prices[(lang, card, variant)] = float(eur)
    return cards, prices


def compute(cards, prices):
    by_set, by_lang, ja_same = {}, {}, {}
    for c in cards:
        for v in c["v"] or []:
            kind = print_kind(v)
            p = prices.get((c["l"], c["c"], v["id"]))
            if kind is None or p is None:
                continue
            r = c["rarity"].lower()
            by_set.setdefault((c["l"], c["s"].lower(), r, kind), []).append(p)
            by_lang.setdefault((c["l"], r, kind), []).append(p)
            if c["l"] == "ja":
                ja_same[(c["s"].lower(), str(c["n"]).lstrip("0"), kind)] = p
    out, stats = [], {}
    for c in cards:
        for v in c["v"] or []:
            if (c["l"], c["c"], v["id"]) in prices:
                continue
            kind = print_kind(v)
            st = stats.setdefault(c["l"], {"missing": 0, "ja_same_card": 0, "set_rarity": 0, "language_rarity": 0})
            st["missing"] += 1
            if kind is None:
                continue
            r = c["rarity"].lower()
            value, basis, n = None, None, 0
            if c["l"] in ("ko", "zh-tw", "zh-cn"):
                same = ja_same.get((c["s"].lower(), str(c["n"]).lstrip("0"), kind))
                if same:
                    value, basis, n = same, "ja_same_card", 1
            if value is None and r in BULK:
                group = by_set.get((c["l"], c["s"].lower(), r, kind)) or []
                if len(group) >= SET_MIN:
                    value, basis, n = statistics.median(group), "set_rarity", len(group)
                else:
                    group = by_lang.get((c["l"], r, kind)) or []
                    if len(group) >= LANG_MIN:
                        value, basis, n = statistics.median(group), "language_rarity", len(group)
            if value is None:
                continue
            st[basis] += 1
            out.append({"lang": c["l"], "card": c["c"], "variant": v["id"], "eur": round(value, 2),
                        "evidence": {"basis": basis, "n": n, "rarity": c["rarity"]}})
    return out, stats


SAVE = """
DELETE FROM price_reference_candidates WHERE provider={provider};
WITH x AS (SELECT * FROM jsonb_to_recordset({payload}::jsonb)
           AS x(lang text, card text, variant text, eur numeric, evidence jsonb))
INSERT INTO price_reference_candidates(language_code,card_id,variant_id,provider,price_eur,currency,evidence,
  verification_status,observed_at)
SELECT lang,card,variant,{provider},eur,'EUR',evidence,'REFERENCE_ONLY',now() FROM x;
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    cards, prices = load()
    rows, stats = compute(cards, prices)
    if a.apply:
        psql(None, stdin="BEGIN;\n" + SAVE.format(provider=lit(PROVIDER),
                                                  payload=lit(json.dumps(rows, ensure_ascii=False))) + "\nCOMMIT;")
    print(json.dumps({"references": len(rows), **stats}))


if __name__ == "__main__":
    main()
