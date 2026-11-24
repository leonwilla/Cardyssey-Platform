"""Cardmarket expansion-list index: product IDs and canonical URLs without search.

Cardmarket's own expansion list pages (``/Products/Singles/<Expansion>?site=N``)
show every product of an expansion with its canonical URL, its printed number
and - in the product image path - its ``idProduct``. The Windows crawler
(``Cardmarket-Expansion-Index.ps1``) stores those tiles in
``cardmarket-expansion-index.json``. This module plans that crawl and applies
the result to the DE/EN browser queues, so that the collector can open the
product page directly instead of using Cardmarket's search (the step that
triggers almost all provider challenges).

An index hint is never a price and never proves a special print. The collector
still validates idProduct, printed number and set on the live product page, and
``import-cardmarket-filtered-prices.py`` keeps its own publication rules.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

# Variants at or above this existing price (or without price) are scanned
# language-exactly in the browser. Cheaper ones keep the official guide price.
MIN_BROWSER_SCAN_EUR = Decimal("2")
TILES_PER_PAGE = 30
INDEX_SCHEMA = 1
PLAN_SCHEMA = 1

VERSIONED = re.compile(r"(?:^|-)V[1-9][0-9]?(?:-|$)", re.IGNORECASE)
FIRST_EDITION = re.compile(r"1\.\s*auflage|1st.edition|first.edition", re.IGNORECASE)
UNLIMITED_SUBTYPES = {"unbegrenzt", "unlimited"}
STANDARD_TYPES = {"normal", "nonholo", "common", "holo", "reverse"}
PRODUCT_PATH = re.compile(r"^[A-Za-z0-9-]{1,120}$")


def _is_empty_stamp(value):
    return str(value or "").strip().lower() in ("", "[]", "null")


def variant_class(row):
    """Classify how Cardmarket can represent a Cardyssey variant.

    STANDARD       normal/holo/reverse, filterable with isReverseHolo.
    FIRST_EDITION  1st edition or unlimited, filterable with isFirstEd.
    SPECIAL        pattern foils, stamps, shadowless, copyright lines, other
                   subtypes: never inferred from a card-level product ID.
    """
    kind = str(row.get("drucktyp") or "").strip().lower()
    foil = str(row.get("foil") or "").strip()
    subtype = str(row.get("sonderdruck") or "").strip().lower()
    stamp = str(row.get("stempel") or "").strip()
    if kind not in STANDARD_TYPES or foil:
        return "SPECIAL"
    stamps = [] if _is_empty_stamp(stamp) else _stamp_list(stamp)
    first = [s for s in stamps if FIRST_EDITION.search(s)]
    if len(first) != len(stamps):
        return "SPECIAL"
    if subtype and subtype not in UNLIMITED_SUBTYPES:
        return "SPECIAL"
    if first or subtype in UNLIMITED_SUBTYPES:
        return "FIRST_EDITION"
    return "STANDARD"


def _stamp_list(value):
    try:
        data = json.loads(value)
        if isinstance(data, list):
            return [str(x) for x in data]
    except (ValueError, TypeError):
        pass
    return [value]


def needs_browser_scan(row, minimum=MIN_BROWSER_SCAN_EUR):
    if str(row.get("needs_price") or "").upper() == "YES":
        return True
    try:
        price = Decimal(str(row.get("existing_price_eur") or "0"))
    except InvalidOperation:
        return True
    return not price.is_finite() or price >= minimum


def slug_number(product):
    """('SVI', 168) for 'Crushing-Hammer-SVI168'; None if no trailing number."""
    m = re.search(r"(?:^|-)([A-Za-z]{0,12})([0-9]{1,4})$", product or "")
    if not m:
        return None
    return m.group(1), m.group(2)


def number_matches(product, printed, set_id="", set_code="", main_prefix=None):
    """Printed-number check against a Cardmarket product slug.

    Port of Test-CardmarketPrintedNumber (cardmarket-search-score.ps1), made
    stricter with the expansion's main slug prefix: in Skyridge 'SK10' is
    card 10 while 'SKH10' is holo card H10 - a plain '10' must not match both.
    """
    expected = str(printed or "").strip()
    if set_id in ("tk-xy-w", "tk-xy-b"):
        suffix = set_id[-1].upper()
        wanted = re.fullmatch(r"(?i)(\d{1,4})([WB]?)", expected)
        actual = re.search(r"(?i)-TK7-?(\d{1,4})" + suffix + "$", product or "")
        return bool(wanted and actual and (not wanted.group(2) or wanted.group(2).upper() == suffix)
                    and int(wanted.group(1)) == int(actual.group(1)))
    if re.fullmatch(r"MCD\d{2}", set_code or ""):
        actual = re.search(r"(?i)-" + re.escape(set_code) + r"-?(\d{1,4})$", product or "")
        return bool(actual and re.fullmatch(r"\d{1,4}", expected) and int(expected) == int(actual.group(1)))
    tail = slug_number(product)
    if not tail:
        return False
    prefix, digits = tail[0].upper(), tail[1]
    main = None if main_prefix is None else main_prefix.upper()
    if re.fullmatch(r"\d{1,4}", expected):
        if main is not None and prefix not in ("", main):
            return False
        return int(expected) == int(digits)
    m = re.fullmatch(r"([A-Za-z]{1,12})0*([0-9]{1,4})", expected)
    if m:
        letters = m.group(1).upper()
        allowed = {letters} | ({main + letters} if main else set())
        return prefix in allowed and int(m.group(2)) == int(digits)
    return False


def main_prefixes(products):
    """Most common slug number prefix per expansion slug ('SK' for Skyridge)."""
    counts = defaultdict(Counter)
    for item in products.values():
        tail = slug_number(item["product"])
        if tail:
            counts[item["slug"]][tail[0].upper()] += 1
    return {slug: c.most_common(1)[0][0] for slug, c in counts.items()}


def normalize_name(name):
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"\bpokemon\b|\btcg\b|\bthe\b", " ", text)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def name_score(a, b):
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = set(na.split()), set(nb.split())
    jaccard = len(ta & tb) / len(ta | tb)
    if na in nb or nb in na:
        jaccard = max(jaccard, 0.8)
    return jaccard


def psql(sql):
    out = subprocess.run(["docker", "exec", "cardyssey-db", "psql", "-X", "-qAt", "-F", "\t",
                          "-v", "ON_ERROR_STOP=1", "-U", "cardyssey", "-d", "cardyssey", "-c", sql],
                         capture_output=True, text=True, check=True).stdout
    return [line.split("\t") for line in out.splitlines() if line]


def load_tcgdex_product_ids():
    """{(language, card_id): idProduct} from cached TCGdex card payloads."""
    rows = psql(r"""
      SELECT split_part(cache_key,'/',5), split_part(cache_key,'/',7),
             payload::jsonb->'pricing'->'cardmarket'->>'idProduct'
        FROM catalog_cache
       WHERE cache_key ~ '^https://api\.tcgdex\.net/v2/[a-z-]+/cards/[^/]+$'
         AND payload LIKE '%"idProduct"%'""")
    return {(lang, card): pid for lang, card, pid in rows if re.fullmatch(r"[0-9]{3,12}", pid or "")}


def load_set_names():
    """{set_id: English (else any) TCGdex set name}."""
    names = {}
    for lang, set_id, name in psql("SELECT language_code,set_id,name FROM catalog_sets_mirror"):
        if lang == "en" or set_id not in names:
            names[set_id] = name
    return names


def set_expansion_votes(tcgdex_ids, catalog):
    votes = defaultdict(Counter)
    for (_, card), pid in tcgdex_ids.items():
        product = catalog.get(int(pid))
        if product:
            votes[card.rsplit("-", 1)[0]][product["idExpansion"]] += 1
    return votes


def set_expansions(tcgdex_ids, catalog, votes=None):
    """Primary Cardmarket idExpansion per Cardyssey set (>= half of TCGdex IDs)."""
    votes = votes or set_expansion_votes(tcgdex_ids, catalog)
    result = {}
    for set_id, counter in votes.items():
        (exp, top), = counter.most_common(1)
        if top >= 0.5 * sum(counter.values()):
            result[set_id] = exp
    return result


def related_expansions(tcgdex_ids, catalog, votes=None):
    """All expansions holding a real share of a set (main set + Additionals)."""
    votes = votes or set_expansion_votes(tcgdex_ids, catalog)
    return {set_id: [exp for exp, n in counter.most_common() if n >= 2 or n >= 0.1 * sum(counter.values())]
            for set_id, counter in votes.items()}


def candidate_ids(row, language, tcgdex_ids):
    other = "en" if language == "de" else "de"
    ids = [tcgdex_ids.get((language, row["cardyssey_karte"])), tcgdex_ids.get((other, row["cardyssey_karte"])),
           row.get("catalog_singleton_id")]
    for field in ("cardmarket_ids", "set_card_candidate_ids"):
        ids += str(row.get(field) or "").split(",")
    seen, out = set(), []
    for pid in ids:
        pid = str(pid or "").strip()
        if re.fullmatch(r"[0-9]{3,12}", pid) and pid not in seen:
            seen.add(pid)
            out.append(pid)
    return out


def build_plan(queues, tcgdex_ids, catalog, overview, set_names, guards, minimum=MIN_BROWSER_SCAN_EUR):
    """Which expansions to crawl, in priority order, with slug candidates."""
    set_exp = set_expansions(tcgdex_ids, catalog)
    targets = Counter()
    exp_sets = defaultdict(set)
    for language, rows in queues.items():
        for row in rows:
            if not needs_browser_scan(row, minimum):
                continue
            exps = set()
            if row["set_id"] in set_exp:
                exps.add(set_exp[row["set_id"]])
            for pid in candidate_ids(row, language, tcgdex_ids):
                product = catalog.get(int(pid))
                if product:
                    exps.add(product["idExpansion"])
            for exp in exps:
                targets[exp] += 1
                exp_sets[exp].add(row["set_id"])
    products_by_exp = defaultdict(list)
    for pid, product in catalog.items():
        products_by_exp[product["idExpansion"]].append(pid)
    overview = [x for x in overview or [] if PRODUCT_PATH.fullmatch(str(x.get("slug") or ""))]
    plan = []
    for exp, count in targets.most_common():
        slugs = []
        for set_id in sorted(exp_sets[exp]):
            if set_exp.get(set_id) == exp and guards.get(set_id):
                slugs.append(guards[set_id])
        names = {set_names.get(s) for s in exp_sets[exp]} - {None}
        scored = sorted(((max((name_score(n, o.get("name")) for n in names), default=0), o["slug"])
                         for o in overview), reverse=True)
        slugs += [slug for score, slug in scored[:4] if score >= 0.34]
        slugs = list(dict.fromkeys(slugs))
        ids = sorted(products_by_exp.get(exp, []))
        plan.append({"idExpansion": exp, "targets": count, "sets": sorted(exp_sets[exp]),
                     "slugCandidates": slugs, "expectedProducts": len(ids),
                     "maxPages": max(1, math.ceil(len(ids) / TILES_PER_PAGE)) + 1,
                     "expectedProductIds": ids})
    return {"schema": PLAN_SCHEMA, "expansions": plan,
            "summary": {"expansions": len(plan), "targetVariants": sum(targets.values()),
                        "estimatedPages": sum(p["maxPages"] - 1 for p in plan),
                        "withoutSlugCandidate": sum(1 for p in plan if not p["slugCandidates"])}}


def load_index(data, product_lines=()):
    """Expansion crawl state plus product tiles (JSONL lines, last one wins)."""
    if not data or data.get("schema") != INDEX_SCHEMA:
        return {}, {}
    expansions = {str(k): v for k, v in (data.get("expansions") or {}).items()}
    products = {}
    for line in product_lines:
        try:
            item = json.loads(line.lstrip("\ufeff"))
        except (ValueError, TypeError):
            continue
        pid, slug, product = str(item.get("id") or ""), str(item.get("slug") or ""), str(item.get("product") or "")
        exp = expansions.get(str(item.get("idExpansion") or ""))
        if not (re.fullmatch(r"[0-9]{3,12}", pid) and PRODUCT_PATH.fullmatch(slug) and PRODUCT_PATH.fullmatch(product)):
            continue
        if not exp or exp.get("slugVerified") is not True or exp.get("slug") != slug:
            continue
        products[pid] = {"slug": slug, "product": product, "idExpansion": str(item["idExpansion"]),
                         "title": str(item.get("title") or "")}
    return expansions, products


def index_set_guards(expansions, set_exp):
    """set_id -> slug for sets whose expansion slug the crawler verified."""
    by_exp = defaultdict(list)
    for set_id, exp in set_exp.items():
        by_exp[str(exp)].append(set_id)
    guards = {}
    for exp, info in expansions.items():
        if info.get("slugVerified") is True and PRODUCT_PATH.fullmatch(str(info.get("slug") or "")):
            for set_id in by_exp.get(exp, []):
                guards[set_id] = info["slug"]
    return guards


INDEX_COLUMNS = ("variant_class", "index_status", "index_product_id", "index_product_url", "index_candidate_urls",
                 "index_previous_id")


def apply_index(rows, language, products, expansions, tcgdex_ids, catalog, set_exp, set_codes=None,
                minimum=MIN_BROWSER_SCAN_EUR, related=None):
    """Add index hints to one language queue in place. Returns status counts."""
    set_codes = set_codes or {}
    related = related or {}
    prefixes = main_prefixes(products)
    by_slug = defaultdict(list)
    for pid, item in products.items():
        by_slug[item["slug"]].append((pid, item))
    verified_slug = {exp: info["slug"] for exp, info in expansions.items()
                     if info.get("slugVerified") is True and PRODUCT_PATH.fullmatch(str(info.get("slug") or ""))}
    guards = index_set_guards(expansions, set_exp)
    standard_types = defaultdict(set)
    for row in rows:
        if variant_class(row) == "STANDARD":
            standard_types[row["cardyssey_karte"]].add(str(row.get("drucktyp") or "").strip().lower())
    stats = Counter()
    for row in rows:
        for column in INDEX_COLUMNS:
            row[column] = ""
        cls = variant_class(row)
        kind = str(row.get("drucktyp") or "").strip().lower()
        kinds = standard_types[row["cardyssey_karte"]]
        if (cls == "STANDARD" and kind in ("normal", "nonholo", "common", "holo")
                and "holo" in kinds and kinds & {"normal", "nonholo", "common"}):
            # Cardmarket has no holo/non-holo offer filter; the same product
            # would give both variants the same price. Human review decides.
            cls = "HOLO_NORMAL_SAME_CARD"
        row["variant_class"] = cls
        if not needs_browser_scan(row, minimum):
            row["index_status"] = "GUIDE_PRICE_BELOW_THRESHOLD"
            stats[row["index_status"]] += 1
            continue
        primary = guards.get(row["set_id"])
        slugs = [verified_slug[str(e)] for e in related.get(row["set_id"], [set_exp.get(row["set_id"])])
                 if str(e) in verified_slug]
        if primary and primary not in slugs:
            slugs.insert(0, primary)
        if not slugs:
            row["index_status"] = "SET_NOT_INDEXED"
            stats[row["index_status"]] += 1
            continue
        code = str(set_codes.get(row["set_id"]) or "")
        matches = sorted((pid, item) for slug in slugs for pid, item in by_slug.get(slug, [])
                         if number_matches(item["product"], row["kartennummer"], row["set_id"], code,
                                           prefixes.get(slug)))
        urls = [f"https://www.cardmarket.com/{language}/Pokemon/Products/Singles/{item['slug']}/{item['product']}"
                for _, item in matches]
        main = [m for m in matches if m[1]["slug"] == primary]
        if not matches:
            row["index_status"] = "NO_NUMBER_MATCH_IN_SET"
        elif cls in ("SPECIAL", "HOLO_NORMAL_SAME_CARD"):
            row["index_status"] = "REVIEW_" + cls
            row["index_candidate_urls"] = json.dumps(urls[:6])
        elif str(row.get("routing_state") or "") == "VERIFIED_PRODUCT_ID":
            row["index_status"] = "HUMAN_ROUTE_KEPT"
        elif not main:
            # Only a secondary expansion (e.g. "Additionals") has this number.
            row["index_status"] = "REVIEW_SECONDARY_EXPANSION_ONLY"
            row["index_candidate_urls"] = json.dumps(urls[:6])
        else:
            pick = None
            plain = [m for m in main if not VERSIONED.search(m[1]["product"])]
            if len(main) == 1:
                pick = main[0]
            elif len(plain) == 1:
                pick = plain[0]
            else:
                ids = candidate_ids(row, language, tcgdex_ids)
                chosen = [m for m in main if m[0] in ids[:2]]
                if len(chosen) == 1:
                    pick = chosen[0]
            current = str(row.get("catalog_singleton_id") or "")
            if not pick:
                row["index_status"] = "AMBIGUOUS_NUMBER_IN_SET"
                row["index_candidate_urls"] = json.dumps(urls[:6])
            else:
                pid, item = pick
                # Cardmarket's own list (image idProduct + slug number) beats a
                # name-based catalog singleton or a TCGdex ID: same-name cards
                # such as Skyridge Staryu 103/104 were swapped there.
                corrected = bool(current and current != pid)
                product = catalog.get(int(pid))
                row["catalog_singleton_id"] = pid
                if product:
                    row["catalog_expansion_id"] = str(product["idExpansion"])
                row["index_product_id"] = pid
                row["index_product_url"] = (f"https://www.cardmarket.com/{language}/Pokemon/Products/Singles/"
                                            f"{item['slug']}/{item['product']}")
                row["index_status"] = "DIRECT_PRODUCT_URL_ID_CORRECTED" if corrected else "DIRECT_PRODUCT_URL"
                if corrected:
                    row["index_previous_id"] = current
        stats[row["index_status"]] += 1
    return stats
