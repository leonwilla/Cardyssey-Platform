#!/usr/bin/env python3
"""eBay sold prices (eBay.de "verkaufte Artikel") for rare DE/EN cards.

Pipeline (owner decisions 26.11.2026):
  --plan    write the search queue for the Windows collector
            (scripts/ebay/Ebay-Sold-Collector.ps1): rare cards (not bulk),
            never checked first, then the oldest check.
  --import  read the collector's results, match sales strictly per variant
            (scripts/ebay/ebay_listing_match.py), store them and recompute
            the eBay value.

Value = median of the matching sales of the last 30 days; with fewer than
three sales the window grows: 60 days, 90 days, 6 months, 1 year. Links (and
the list of sales in the app) only for sales of the last 30 days; older sales
are kept only as date + price for the price graph.
"""
import argparse
import json
import re
import statistics
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ebay_listing_match as em  # noqa: E402
import ebay_listing_fallback as ef  # noqa: E402

BASE = Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/EbaySold")
QUEUE = BASE / "ebay-sold-queue.json"
RESULTS = BASE / "ebay-sold-results.jsonl"
OFFSET = Path.home() / ".local/state/cardyssey-ebay-sold-offset.json"
WINDOWS = ((30, "30 Tage"), (60, "60 Tage"), (90, "90 Tage"), (182, "6 Monate"), (365, "1 Jahr"))
LINK_DAYS = 30
MIN_SALES = 3
REFRESH_DAYS = 14
MONTHS = {"jan": 1, "feb": 2, "mär": 3, "mar": 3, "mrz": 3, "apr": 4, "mai": 5, "may": 5, "jun": 6, "jul": 7,
          "aug": 8, "sep": 9, "okt": 10, "oct": 10, "nov": 11, "dez": 12, "dec": 12}
SOLD = re.compile(r"Verkauft\s+(\d{1,2})\.?\s+([A-Za-zäÄ]{3,4})\.?\s+(\d{4})")
PRICE = re.compile(r"EUR\s*([0-9.]+,[0-9]{2})")
ITEM_ID = re.compile(r"/itm/(?:[^/]+/)?(\d{9,15})")


def psql(sql, stdin=None):
    return ef.psql(sql, stdin)


lit = ef.lit

RARE_CARDS = """
SELECT json_build_object('lang', g.language_code, 'card', g.card_id,
  'checked', (SELECT checked_at FROM ebay_sold_checks k WHERE k.language_code=g.language_code AND k.card_id=g.card_id))
FROM (SELECT DISTINCT language_code, card_id FROM global_price_source_policy
      WHERE language_code IN ('de','en') AND price_class='SPECIAL') g
"""


def plan(limit):
    """Queue: never checked first, then the oldest check older than REFRESH_DAYS."""
    now = datetime.now(timezone.utc)
    rows = [json.loads(l) for l in psql(RARE_CARDS).splitlines()]
    due = []
    for r in rows:
        checked = datetime.fromisoformat(r["checked"]) if r["checked"] else None
        if checked and now - checked < timedelta(days=REFRESH_DAYS):
            continue
        due.append((checked or datetime.min.replace(tzinfo=timezone.utc), r["lang"], r["card"]))
    due.sort()
    wanted = {(l, c) for _, l, c in due[:limit]}
    cards = {}
    for l in psql(ef.TARGETS).splitlines():
        c = json.loads(l)
        if (c["lang"], c["card"]) in wanted:
            cards[(c["lang"], c["card"])] = c
    queue = [{"key": f"{l}|{c}", "query": ef.query_for(cards[(l, c)])} for _, l, c in due[:limit] if (l, c) in cards]
    BASE.mkdir(parents=True, exist_ok=True)
    tmp = QUEUE.with_suffix(".tmp")
    tmp.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    tmp.replace(QUEUE)
    return {"due": len(due), "queued": len(queue)}


def parse_item(item, today):
    """(title, eur, sold_on, item_id, url) of one sold result row, or None."""
    text = item.get("text") or ""
    title = re.sub(r"\s*Wird in neuem Fenster oder Tab geöffnet.*", "", item.get("title") or "").strip()
    title = re.sub(r"^Neues Angebot\s*", "", title)
    if not title or title == "Shop on eBay" or " bis EUR" in text:
        return None  # placeholder or multi-variation listing (price range)
    m, p, i = SOLD.search(text), PRICE.search(text), ITEM_ID.search(item.get("url") or "")
    if not (m and p and i):
        return None
    month = MONTHS.get(m.group(2).lower()[:3]) or MONTHS.get(m.group(2).lower())
    if not month:
        return None
    try:
        sold_on = date(int(m.group(3)), month, int(m.group(1)))
    except ValueError:
        return None
    if sold_on > today:
        return None
    eur = float(p.group(1).replace(".", "").replace(",", "."))
    return title, eur, sold_on, i.group(1), f"https://www.ebay.de/itm/{i.group(1)}"


SAVE_SALES = """
WITH x AS (SELECT * FROM jsonb_to_recordset({payload}::jsonb)
  AS x(card text, variant text, item text, sold date, eur numeric, title text, url text))
INSERT INTO ebay_sold_history(card_id,language_code,variant_id,ebay_item_id,sold_on,sold_eur,condition_label,
  condition_assumed,variant_assumed,title,listing_url,identity_basis)
SELECT card,{lang},variant,item,sold,eur,'NEAR_MINT',true,false,title,url,'sold_search_title_number_variant' FROM x
ON CONFLICT(card_id,language_code,variant_id,ebay_item_id) DO UPDATE SET last_collected_at=now();
-- Links only for the last 30 days (owner decision): older sales keep date + price for the graph.
UPDATE ebay_sold_history SET listing_url='', title=''
WHERE language_code={lang} AND sold_on < current_date - {link_days} AND listing_url<>'';
"""

CHECKS = """
WITH x AS (SELECT * FROM jsonb_to_recordset({payload}::jsonb) AS x(lang text, card text, items int, sales int))
INSERT INTO ebay_sold_checks(language_code,card_id,checked_at,items_seen,sales_matched)
SELECT lang,card,now(),items,sales FROM x
ON CONFLICT(language_code,card_id) DO UPDATE SET checked_at=now(), items_seen=EXCLUDED.items_seen,
  sales_matched=EXCLUDED.sales_matched;
"""


def value_for(sales, today):
    """sales: [(sold_on, eur, title, url, item)] -> cache row or None."""
    for days, label in WINDOWS:
        used = [s for s in sales if s[0] >= today - timedelta(days=days)]
        if len(used) >= MIN_SALES:
            prices = sorted(s[1] for s in used)
            used.sort(key=lambda s: s[0], reverse=True)
            recent = [{"itemId": s[4], "title": s[2] or "eBay-Verkauf", "soldPriceEur": s[1],
                       "endedAt": f"{s[0].isoformat()}T00:00:00Z", "rawCondition": None,
                       "url": s[3] if s[0] >= today - timedelta(days=LINK_DAYS) and s[3] else None}
                      for s in used[:10]]
            return {"median": round(statistics.median(prices), 2), "low": prices[0], "high": prices[-1],
                    "n": len(used), "days": days, "label": label, "recent": recent}
    return None


CACHE = """
WITH x AS (SELECT * FROM jsonb_to_recordset({payload}::jsonb)
  AS x(card text, variant text, median numeric, low numeric, high numeric, n int, days int, label text, recent jsonb))
INSERT INTO ebay_price_cache(card_id,language_code,variant_id,source,base_eur,range_low_eur,range_high_eur,sample_count,
  updated_at,recent_sales,price_window_days,price_window_label,low_sample)
SELECT card,{lang},variant,'CARDYSSEY_EBAY',median,low,high,n,now(),recent,days,label,false FROM x
ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET source=EXCLUDED.source, base_eur=EXCLUDED.base_eur,
  range_low_eur=EXCLUDED.range_low_eur, range_high_eur=EXCLUDED.range_high_eur, sample_count=EXCLUDED.sample_count,
  updated_at=now(), recent_sales=EXCLUDED.recent_sales, price_window_days=EXCLUDED.price_window_days,
  price_window_label=EXCLUDED.price_window_label, low_sample=false;
"""


def history(lang, keys):
    """All stored sales of these variants (ours and the older collector's)."""
    if not keys:
        return {}
    cards = ",".join(lit(c) for c in sorted({c for c, _ in keys}))
    out = {}
    sql = (f"SELECT json_build_object('c',card_id,'v',variant_id,'d',sold_on,'e',sold_eur,'t',title,'u',listing_url,"
           f"'i',ebay_item_id) FROM ebay_sold_history WHERE language_code={lit(lang)} AND card_id IN ({cards})")
    for line in psql(sql).splitlines():
        x = json.loads(line)
        if (x["c"], x["v"]) in keys:
            out.setdefault((x["c"], x["v"]), []).append(
                (date.fromisoformat(x["d"]), float(x["e"]), x["t"], x["u"], x["i"]))
    return out


def import_results(dry_run=False):
    try:
        offset = json.loads(OFFSET.read_text())["offset"]
    except (OSError, ValueError, KeyError):
        offset = 0
    if not RESULTS.exists():
        return {"pages": 0}
    raw = RESULTS.read_bytes()
    if offset > len(raw):
        offset = 0  # file was replaced
    lines = raw[offset:].decode("utf-8-sig", errors="replace").splitlines()
    today = date.today()
    wanted = set()
    for line in lines:
        try:
            wanted.add(tuple(json.loads(line.lstrip("\ufeff"))["key"].split("|", 1)))
        except (ValueError, KeyError):
            continue
    targets = {}
    for l in psql(ef.TARGETS).splitlines():
        c = json.loads(l)
        if (c["lang"], c["card"]) in wanted:
            targets[(c["lang"], c["card"])] = c
    stats = {"pages": 0, "items": 0, "sales": 0, "variants_valued": 0}
    sales_by_lang, checks, touched = {"de": [], "en": []}, [], {"de": set(), "en": set()}
    for line in lines:
        try:
            page = json.loads(line.lstrip("﻿"))
        except ValueError:
            continue
        lang, card_id = page["key"].split("|", 1)
        card = targets.get((lang, card_id))
        stats["pages"] += 1
        if not card:
            continue
        parsed = [p for p in (parse_item(i, today) for i in page.get("items") or []) if p]
        stats["items"] += len(parsed)
        # Every variant of the card (ebay_listing_fallback.evaluate only
        # looks at "missing" variants; sold values are wanted for all).
        card = dict(card, missing=[v["id"] for v in card["variants"] or []])
        items = [{"title": t, "price": {"value": e, "currency": "EUR"}, "itemWebUrl": u, "itemId": i,
                  "_sold": s.isoformat()} for t, e, s, i, u in parsed]
        by_url = {it["itemWebUrl"]: it for it in items}
        matched = 0
        for r in ef.evaluate(card, items):
            if r["status"] != "OK":
                continue
            for o in r["offers"]:
                it = by_url.get(o["url"])
                if not it:
                    continue
                sales_by_lang[lang].append({"card": card_id, "variant": r["variant"], "item": it["itemId"],
                                            "sold": it["_sold"], "eur": it["price"]["value"],
                                            "title": it["title"][:200], "url": it["itemWebUrl"]})
                touched[lang].add((card_id, r["variant"]))
                matched += 1
        stats["sales"] += matched
        checks.append({"lang": lang, "card": card_id, "items": len(parsed), "sales": matched})
    if dry_run:
        return stats
    for lang, rows in sales_by_lang.items():
        for i in range(0, len(rows), 500):
            psql(None, stdin="BEGIN;\n" + SAVE_SALES.format(payload=lit(json.dumps(rows[i:i + 500], ensure_ascii=False)),
                                                             lang=lit(lang), link_days=LINK_DAYS) + "\nCOMMIT;")
    for i in range(0, len(checks), 500):
        psql(None, stdin="BEGIN;\n" + CHECKS.format(payload=lit(json.dumps(checks[i:i + 500]))) + "\nCOMMIT;")
    for lang, keys in touched.items():
        values = []
        for (card_id, variant), sales in history(lang, keys).items():
            v = value_for(sales, today)
            if v:
                values.append({"card": card_id, "variant": variant, **v})
        for i in range(0, len(values), 300):
            psql(None, stdin="BEGIN;\n" + CACHE.format(payload=lit(json.dumps(values[i:i + 300], ensure_ascii=False)),
                                                        lang=lit(lang)) + "\nCOMMIT;")
        stats["variants_valued"] += len(values)
    OFFSET.parent.mkdir(parents=True, exist_ok=True)
    OFFSET.write_text(json.dumps({"offset": len(raw)}))
    return stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan", action="store_true")
    p.add_argument("--import", dest="do_import", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=400)
    a = p.parse_args()
    out = {}
    if a.do_import:
        out["import"] = import_results(a.dry_run)
    if a.plan:
        out["plan"] = plan(a.limit)
    print(json.dumps(out, default=str))


if __name__ == "__main__":
    main()
