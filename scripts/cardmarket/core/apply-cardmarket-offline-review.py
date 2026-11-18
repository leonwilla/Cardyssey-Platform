#!/usr/bin/env python3
"""Apply verified page decisions and historical candidates without touching the scan queue."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from cardmarket_print_routes import (
    ROOT, SET_SLUGS, observations, official_products, product_ids,
    product_path, read_list, reference_urls, token, vintage_page_index, vintage_subtype,
)

BASE = Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector")
EVIDENCE = "cardmarket-offline-review-evidence.json"
STAMP_REASON = "CATALOG_ID_AND_CARD_NUMBER_VERIFIED_EXACT_PRINT_UNVERIFIED"
BASE_ROUTE_EVIDENCE = "Offline verified Base Set unlimited original product page"
STAMP_ROUTE_EVIDENCE = "Official singleton product page; exact stamped print unverified"


def is_unlimited(row):
    return (
        row.get("set_id") == "base1"
        and token(row.get("sonderdruck")) in {"unlimited", "unbegrenzt"}
        and str(row.get("stempel") or "").strip() in ("", "[]")
        and not str(row.get("foil") or "").strip()
    )


def base_pages(queues, history, products, seeds):
    """Use live-number evidence and published canonical Base Set references."""
    catalog_ids, observed = vintage_page_index(queues, history, products)
    result = {}
    for rows in queues.values():
        for row in rows:
            if not is_unlimited(row):
                continue
            number = str(row.get("kartennummer") or "")
            if not number.isdecimal() or not 1 <= int(number) <= 102:
                continue
            key = row["cardyssey_karte"], number
            pages = {
                (pid, sku) for slug, sku, pid in observed.get(key, ())
                if slug == "Base-Set" and re.search(r"-V1-BS0*" + str(int(number)) + "$", sku, re.I)
            }
            seed = seeds.get(str(int(number)))
            if seed:
                pid, sku = seed["productId"], seed["sku"]
                known = catalog_ids.get(key, set())
                # #73 is absent from the name-based queue under an alternate
                # spelling. Its published BS73 page and official ID are pinned.
                if ((not known or pid in known) and str(products.get(pid, {}).get("idExpansion")) == "1523"
                    and (re.search(r"-V1-BS0*" + str(int(number)) + "$", sku, re.I)
                         or (int(number) == 87 and sku == "Pokedex-BS87"))):
                    pages.add((pid, sku))
            if len(pages) == 1:
                pid, sku = next(iter(pages))
                if str(products.get(pid, {}).get("idExpansion")) == "1523":
                    result[key] = (pid, f"Base-Set/{sku}")
    return result


def catalog_name(product):
    name = str(product.get("name") or "").casefold().strip()
    return re.sub(r"\s*\((?:v\.?\s*\d+|prize\s+pack[^)]*|additionals[^)]*)\)\s*$", "", name)


def singleton_stamp(row, entry, products, families, names, regular_expansions):
    if entry.get("error") != STAMP_REASON or entry.get("catalog_direct_id_verified") is not True:
        return None
    stamps = read_list(row.get("stempel"))
    if not stamps or vintage_subtype(row) or any(token(s) in {"1st-edition", "first-edition", "1.-auflage"} for s in stamps):
        return None
    if entry.get("card_number_url_verified") is not True or entry.get("set_id") != row.get("set_id"):
        return None
    pid = str(entry.get("product_id") or "")
    product = products.get(pid)
    if not product or pid != row.get("catalog_singleton_id") or str(product["idExpansion"]) != row.get("catalog_expansion_id"):
        return None
    path = product_path(entry.get("url"))
    if not path or path[2] != SET_SLUGS.get(row.get("set_id")):
        return None
    if re.search(r"(?:^|-)V(?:[2-9]|[1-9]\d+)(?:-|$)", path[3], re.I):
        return None
    family = str(product.get("idMetacard") or "")
    name = catalog_name(product)
    if not family.isdecimal() or int(family) <= 0 or not name:
        return None
    if any(product_path(u) and product_path(u)[2] != path[2] for u in reference_urls(row, path[1])):
        return None
    expansion = str(product["idExpansion"])
    alternatives = (families[family] | names[name] | product_ids(row)) - {pid}
    # Other independently matched main sets are reprints. A second item in
    # this expansion, a special expansion, or an unresolved expansion is
    # still a plausible alternate page for the stamped print.
    for alt in alternatives:
        target = str(products.get(alt, {}).get("idExpansion") or "")
        if target == expansion or target not in regular_expansions:
            return None
    return pid, f"{path[2]}/{path[3]}"


def historical_date(timestamp, day):
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Berlin")).date().isoformat() == day
    except (ValueError, AttributeError):
        return False


def review_evidence(queues, history, products, seeds, versions, day):
    result = {}
    base = base_pages(queues, history, products, seeds)
    families = defaultdict(set)
    names = defaultdict(set)
    for pid, product in products.items():
        families[str(product.get("idMetacard") or "")].add(pid)
        names[catalog_name(product)].add(pid)
    expansions = defaultdict(set)
    for rows in queues.values():
        for row in rows:
            pid = row.get("catalog_singleton_id")
            eid = row.get("catalog_expansion_id")
            guard = SET_SLUGS.get(row.get("set_id"))
            if guard and eid and str(products.get(pid, {}).get("idExpansion")) == eid:
                expansions[eid].add(guard)
    regular_expansions = {eid for eid, guards in expansions.items() if len(guards) == 1}
    for language, rows in queues.items():
        by_print = {(r["cardyssey_karte"], r["variante_id"]): r for r in rows}
        latest = {(e.get("card_id"), e.get("variant_id")): e for e in history[language]}
        candidates = versions(
            [e for e in history[language] if historical_date(e.get("seen_at"), day)],
            by_print, SET_SLUGS, language,
        )
        localized = {}
        for (card, variant), row in by_print.items():
            entry = latest.get((card, variant), {})
            base_match = base.get((card, row.get("kartennummer"))) if is_unlimited(row) else None
            stamp_match = singleton_stamp(row, entry, products, families, names, regular_expansions)
            match = base_match or stamp_match
            if match:
                pid, path = match
                localized[f"{card}|{variant}"] = {
                    "kind": "base_unlimited" if base_match else "singleton_stamp",
                    "language": language, "card": card, "variant": variant, "product": pid,
                    "url": f"https://www.cardmarket.com/{language}/Pokemon/Products/Singles/{path}",
                    "exact_print_filter_supported": bool(base_match),
                }
            elif (card, variant) in candidates:
                localized[f"{card}|{variant}"] = {
                    "kind": "version_candidates",
                    "urls": candidates[(card, variant)],
                    "exact_print_filter_supported": False,
                }
        result[language] = localized
    return result


def sql_apply(rows):
    payload = "'" + json.dumps(rows, ensure_ascii=False).replace("'", "''") + "'"
    # Verify the metadata against the live catalog before writing a Base Set route.
    sql = f"""
BEGIN;
CREATE TEMP TABLE offline_prints ON COMMIT DROP AS
 SELECT data.*, CASE WHEN kind='base_unlimited' THEN '{BASE_ROUTE_EVIDENCE}'
                     ELSE '{STAMP_ROUTE_EVIDENCE}' END AS proof
 FROM jsonb_to_recordset({payload}::jsonb)
 AS data(kind text,language text,card text,variant text,product text,url text)
 JOIN catalog_cards_mirror c ON c.language_code=data.language AND c.card_id=data.card
 WHERE EXISTS (SELECT 1 FROM jsonb_array_elements(c.variants) v
  WHERE v->>'id'=data.variant AND
    ((data.kind='base_unlimited' AND c.set_id='base1'
      AND lower(v->>'subtype') IN ('unlimited','unbegrenzt')
      AND COALESCE(v->>'foil','')='' AND COALESCE(v->>'stamps','[]') IN ('','[]'))
     OR (data.kind='singleton_stamp' AND jsonb_typeof(v->'stamps')='array' AND v->'stamps'<>'[]'::jsonb)));
WITH changed AS (
 INSERT INTO price_source_routing AS route(language_code,card_id,variant_id,primary_provider,
    provider_product_id,provider_product_url,source_evidence,verification_state)
 SELECT language,card,variant,'CARDMARKET',product,url,proof,
        CASE WHEN kind='base_unlimited' THEN 'VERIFIED_PRODUCT_ID' ELSE 'SOURCE_ONLY' END
 FROM offline_prints
 ON CONFLICT(language_code,card_id,variant_id) DO UPDATE SET
   primary_provider='CARDMARKET',provider_product_id=EXCLUDED.provider_product_id,
   provider_product_url=EXCLUDED.provider_product_url,source_evidence=EXCLUDED.source_evidence,
   verification_state=EXCLUDED.verification_state,updated_at=now(),
   fallback_provider=CASE WHEN route.primary_provider<>'CARDMARKET'
       THEN COALESCE(route.fallback_provider,route.primary_provider) ELSE route.fallback_provider END
 WHERE route.verification_state<>'VERIFIED_PRODUCT_ID'
   AND (EXCLUDED.verification_state='VERIFIED_PRODUCT_ID' OR route.primary_provider='CARDMARKET')
   AND (route.provider_product_id,route.provider_product_url,route.source_evidence,route.verification_state)
    IS DISTINCT FROM (EXCLUDED.provider_product_id,EXCLUDED.provider_product_url,EXCLUDED.source_evidence,EXCLUDED.verification_state)
 RETURNING language_code,verification_state
)
SELECT json_build_object('routesChanged',count(*),'baseRoutesChanged',count(*) FILTER (WHERE verification_state='VERIFIED_PRODUCT_ID'))::text FROM changed;
WITH reviewed AS (
 UPDATE cardmarket_print_identity_review r SET
   candidate_ids=jsonb_build_array(e.product),matched_set_ids=jsonb_build_array(e.product),
   selected_product_id=CASE WHEN e.kind='base_unlimited' THEN e.product ELSE r.selected_product_id END,
   status=CASE WHEN e.kind='base_unlimited' THEN 'CONFIRMED_PRINT' ELSE r.status END,
   classification=CASE WHEN e.kind='base_unlimited' THEN 'OFFLINE_BASE_UNLIMITED_VERIFIED' ELSE 'SINGLETON_PAGE_LINKED_PRINT_PENDING' END,
   reviewer_note=e.proof,checked_at=now(),
   reviewed_at=CASE WHEN e.kind='base_unlimited' THEN now() ELSE r.reviewed_at END
 FROM offline_prints e JOIN price_source_routing p ON p.language_code=e.language AND p.card_id=e.card
   AND p.variant_id=e.variant AND p.primary_provider='CARDMARKET' AND p.provider_product_id=e.product
   AND p.provider_product_url=e.url
 WHERE r.language_code=e.language AND r.card_id=e.card AND r.variant_id=e.variant
   AND r.status='PENDING_REVIEW' AND (r.selected_product_id IS NULL OR r.selected_product_id=e.product)
   AND ((e.kind='base_unlimited' AND p.verification_state='VERIFIED_PRODUCT_ID')
        OR (e.kind='singleton_stamp' AND p.verification_state='SOURCE_ONLY' AND r.classification<>'SINGLETON_PAGE_LINKED_PRINT_PENDING'))
 RETURNING r.status
)
SELECT json_build_object('reviewRowsChanged',count(*),'baseReviewsConfirmed',count(*) FILTER (WHERE status='CONFIRMED_PRINT'))::text FROM reviewed;
COMMIT;
"""
    cmd = ["docker","exec","-i","cardyssey-db","psql","-X","-qAt","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"]
    process = subprocess.run(cmd, input=sql, text=True, capture_output=True, check=True, timeout=60)
    return {k: v for line in process.stdout.splitlines() if line.startswith("{") for k, v in json.loads(line).items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=BASE)
    parser.add_argument("--day", default="2026-11-10")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    resolver = importlib.util.spec_from_file_location("offline_resolver", Path(__file__).with_name("resolve-multiple-search-hits.py"))
    module = importlib.util.module_from_spec(resolver)
    resolver.loader.exec_module(module)
    queues = {}
    history = {}
    for language in ("de", "en"):
        with (args.base / f"queue-{language}.csv").open(encoding="utf-8-sig", newline="") as stream:
            queues[language] = list(csv.DictReader(stream))
        history[language] = list(observations(args.base, language))
    products, feed_date = official_products()
    if len(products) < 50000:
        raise ValueError("official Cardmarket product feed is incomplete")
    seeds = json.loads((ROOT / "config/cardmarket-base-set-unlimited-pages.json").read_text(encoding="utf-8"))
    result = review_evidence(queues, history, products, seeds, module.resolve_set_version_candidates, args.day)
    report = {
        "day": args.day, "feedDate": feed_date, "applied": args.apply,
        "languages": {lang: dict(Counter(e["kind"] for e in entries.values())) for lang, entries in result.items()},
        "unlimitedWithoutProof": {lang: sum(is_unlimited(r) for r in rows)
                                  - sum(e["kind"] == "base_unlimited" for e in result[lang].values())
                                 for lang, rows in queues.items()},
        "versionUrls": sum(len(e.get("urls", ())) for entries in result.values() for e in entries.values()),
    }
    if args.apply:
        rows = [e for entries in result.values() for e in entries.values() if e["kind"] != "version_candidates"]
        report.update(sql_apply(rows))
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.base, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({"schema":1,"generatedAt":datetime.now(timezone.utc).isoformat(),"languages":result},
                      stream, ensure_ascii=False, indent=2)
        try:
            os.replace(temporary, args.base / EVIDENCE)
        finally:
            temporary.unlink(missing_ok=True)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
