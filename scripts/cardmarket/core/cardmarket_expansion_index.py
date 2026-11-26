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
MIN_BROWSER_SCAN_EUR = Decimal("20")
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
    """('SVI', 168) for 'Crushing-Hammer-SVI168', ('30C', '084') for
    'Seismitoad-30C084'; None if no trailing number."""
    m = re.search(r"(?:^|-)((?:[0-9]{0,3}[A-Za-z]{1,12})?)([0-9]{1,4})$", product or "")
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


TITLE_NUMBER = re.compile(r"\(([A-Za-z0-9]{1,6}) ([A-Za-z]{0,4})([0-9]{1,4})\)\s*$")


def title_number(product, title):
    """Printed number from Cardmarket's title when the slug has none.

    Sword & Shield era slugs carry no number ('Excadrill', 'Cramorant-V2');
    the title does ('Excadrill (FST 183)', 'Cramorant (SHF SV30)'). Returns
    (letters, digits) such as ('', '183') or ('SV', '30'); None when the
    slug already ends in a number (a bare V1/V2 version marker is none)."""
    tail = slug_number(product)
    if tail and tail[0].upper() != "V":
        return None
    m = TITLE_NUMBER.search(title or "")
    return (m.group(2).upper(), m.group(3)) if m else None


# 30th Celebration reprints keep their original number: 'Charizard (30C BS 4)'.
# Our set 30th-c numbers them 001-030, so they are matched by name only.
REPRINT_TITLE = re.compile(r"\(30C [A-Za-z]{1,6} [0-9]{1,4}\)\s*$")
NAME_MATCH_SETS = {"30th-c"}


def title_number_matches(number, printed):
    """Exact letters and number: plain '10' never matches shiny 'SV10'."""
    m = re.fullmatch(r"([A-Za-z]{0,12}?)0*([0-9]{1,4})", str(printed or "").strip())
    return bool(m and number and m.group(1).upper() == number[0] and int(m.group(2)) == int(number[1]))


def main_prefixes(products):
    """Most common slug number prefix per expansion slug ('SK' for Skyridge)."""
    counts = defaultdict(Counter)
    for item in products.values():
        if item.get("reprint"):
            continue
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
    """Which expansions to crawl, with slug candidates. ALL expansions with a
    queued card are planned (every card gets its ID/URL); expansions with
    variants worth a browser scan (>= minimum) come first."""
    set_exp = set_expansions(tcgdex_ids, catalog)
    targets = Counter()
    every = Counter()
    exp_sets = defaultdict(set)
    for language, rows in queues.items():
        for row in rows:
            scan = needs_browser_scan(row, minimum)
            exps = set()
            if row["set_id"] in set_exp:
                exps.add(set_exp[row["set_id"]])
            for pid in candidate_ids(row, language, tcgdex_ids):
                product = catalog.get(int(pid))
                if product:
                    exps.add(product["idExpansion"])
            for exp in exps:
                every[exp] += 1
                if scan:
                    targets[exp] += 1
                exp_sets[exp].add(row["set_id"])
    products_by_exp = defaultdict(list)
    for pid, product in catalog.items():
        products_by_exp[product["idExpansion"]].append(pid)
    overview = [x for x in overview or [] if PRODUCT_PATH.fullmatch(str(x.get("slug") or ""))]
    plan = []
    for exp in sorted(every, key=lambda e: (-targets[e], -every[e], e)):
        count = targets[exp]
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
        plan.append({"idExpansion": exp, "targets": count, "allVariants": every[exp], "sets": sorted(exp_sets[exp]),
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
                         "title": str(item.get("title") or ""),
                         "title_number": title_number(product, str(item.get("title") or "")),
                         "reprint": bool(REPRINT_TITLE.search(str(item.get("title") or "")))}
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
                 "index_previous_id", "index_review_group", "index_match")


def _finish(row, status, below, stats):
    """Below the browser threshold the official guide price stays the price
    source; the resolved product ID/URL is kept as information only."""
    if below:
        row["index_match"] = status
        row["index_review_group"] = ""
        row["index_previous_id"] = ""
        status = "GUIDE_PRICE_BELOW_THRESHOLD"
        if row.get("index_product_url"):
            stats["GUIDE_PRICE_BELOW_THRESHOLD_WITH_URL"] += 1
    row["index_status"] = status
    stats[status] += 1

KIND_SYNONYMS = {
    "meisterball": "masterball", "pokéball": "pokeball", "poke-ball": "pokeball", "energie": "energy",
    "kosmos": "cosmos", "galaxie": "galaxy", "schattenlos": "shadowless", "unbegrenzt": "unlimited",
    "copyright-1999-2000": "1999-2000-copyright", "mitarbeiter": "staff", "pokémon-center": "pokemon-center",
    "25.-jubiläum": "25th-celebration", "liga": "league",
}


def _norm_kind(value):
    text = re.sub(r"\s+", "-", str(value or "").strip().lower())
    return KIND_SYNONYMS.get(text, text)


def kind_key(row):
    """Language-independent special attributes of a variant ('' = plain)."""
    stamps = [] if _is_empty_stamp(row.get("stempel")) else _stamp_list(str(row.get("stempel")))
    parts = [_norm_kind(row.get("foil")), _norm_kind(row.get("sonderdruck"))]
    parts += sorted(_norm_kind(x) for x in stamps if not FIRST_EDITION.search(x))
    return "+".join(x for x in parts if x and x != "unlimited")


def filter_key(row):
    """What Cardmarket's offer filters can tell apart: reverse and 1st edition."""
    reverse = "Y" if str(row.get("drucktyp") or "").strip().lower() == "reverse" else "N"
    stamps = "" if _is_empty_stamp(row.get("stempel")) else str(row.get("stempel"))
    return reverse, "Y" if FIRST_EDITION.search(stamps) else "N"


def load_rules(data):
    """{(set_id or '*', kind): rule} from config/cardmarket-variant-version-rules.json."""
    rules = {}
    if not data or data.get("schema") != 1:
        return rules
    for rule in data.get("rules") or []:
        action = rule.get("action")
        version = str(rule.get("version") or "")
        if action not in ("version", "plain") or (action == "version" and not re.fullmatch(r"V[1-9][0-9]?", version)):
            continue
        rules[(str(rule.get("set") or "*"), _norm_kind(rule.get("kind")))] = {"action": action, "version": version}
    return rules


def _pick_plain(main, row, language, tcgdex_ids):
    if len(main) == 1:
        return main[0]
    plain = [m for m in main if not VERSIONED.search(m[1]["product"])]
    if len(plain) == 1:
        return plain[0]
    ids = candidate_ids(row, language, tcgdex_ids)
    chosen = [m for m in main if m[0] in ids[:2]]
    return chosen[0] if len(chosen) == 1 else None


def _variant_ids(row):
    return [x.strip() for x in str(row.get("cardmarket_ids") or "").split(",") if x.strip()]


def _pick_by_variant_ids(row, group, main, guide=None):
    """Pick the product by the per-variant Cardmarket ID (TCGdex variant data).

    Only when it cannot be a guess: every variant of this card/filter key has
    exactly one ID, all IDs differ, and this variant's ID is one of the
    products Cardmarket lists under this card number in the set. With the
    official price guide, a special print priced clearly below the plain
    print of the same card is rejected (such swaps are typical ID mix-ups).
    Checked 26.11.2026: 119 of 119 priced groups were plausible.
    """
    ids = [_variant_ids(r) for r in group]
    if any(len(i) != 1 for i in ids) or len({i[0] for i in ids}) != len(group):
        return None
    own = _variant_ids(row)[0]
    chosen = [m for m in main if m[0] == own]
    if len(chosen) != 1:
        return None
    if guide is not None and kind_key(row):
        plain = [r for r in group if not kind_key(r)]
        if len(plain) == 1:
            def price(pid):
                g = guide.get(int(pid)) or {}
                return g.get("trend") or g.get("avg")
            a, b = price(_variant_ids(plain[0])[0]), price(own)
            if a and b and b < a * 0.9:
                return None
    return chosen[0]


def _product_number_ok(item, printed, code, prefix, set_id):
    if item.get("title_number"):
        return title_number_matches(item["title_number"], printed)
    return number_matches(item["product"], printed, set_id, code, prefix)


def _plain_name(name):
    """Name for the TCGdex ID check: Cardmarket adds level suffixes
    ('Tropius Lv.35') and writes Gold Star as text."""
    text = re.sub(r"\s+lv\.?\s*[0-9]+$", "", str(name or ""), flags=re.I)
    return normalize_name(text.replace("☆", " gold star "))


def _pick_tcgdex_variant(row, card_rows, catalog, allowed_exps, english_name, products, guide, code, prefixes):
    """Last resort: the variant's own Cardmarket ID from TCGdex.

    Used where the set list cannot decide (special prints that Cardmarket
    keeps in a separate "Additionals" expansion, numbers missing from the
    list, unindexed sets). Accepted only when every check holds: exactly one
    ID, no other variant of the card uses it, the official catalog lists it
    as a single in the card's own expansion or its Additionals, the English
    name matches, the printed number matches where Cardmarket's list shows
    it, and a special print is not clearly cheaper than the plain card.
    """
    ids = _variant_ids(row)
    if len(ids) != 1 or not ids[0].isdigit():
        return None
    own = ids[0]
    # Normal and reverse share one product (reverse is a filter there), so
    # only variants with the same filter key must not share the ID.
    if any(own in _variant_ids(r) for r in card_rows if r is not row and filter_key(r) == filter_key(row)):
        return None
    product = catalog.get(int(own))
    if not product or product.get("idCategory") != 51 or str(product.get("idExpansion")) not in allowed_exps:
        return None
    base = str(product.get("name") or "").split(" [", 1)[0]
    if not english_name or _plain_name(base) != _plain_name(english_name):
        return None
    item = products.get(own)
    if item and not _product_number_ok(item, row.get("kartennummer"), code, prefixes.get(item["slug"]),
                                       row.get("set_id", "")):
        return None
    if guide is not None and kind_key(row):
        plain = [r for r in card_rows if not kind_key(r) and filter_key(r) == filter_key(row)] or \
                [r for r in card_rows if not kind_key(r)]
        plain_ids = {i for r in plain for i in _variant_ids(r)}
        if len(plain_ids) == 1:
            def price(pid):
                g = guide.get(int(pid)) or {}
                return g.get("trend") or g.get("avg")
            a, b = price(next(iter(plain_ids))), price(own)
            if a and b and b < a * 0.9:
                return None
    return own, item


def _set_pick(row, alt, language, catalog, below):
    pid, item = alt
    row["index_product_id"] = pid
    row["index_product_url"] = (f"https://www.cardmarket.com/{language}/Pokemon/Products/Singles/"
                                f"{item['slug']}/{item['product']}") if item else ""
    if not below:
        row["catalog_singleton_id"] = pid
        product = catalog.get(int(pid))
        if product:
            row["catalog_expansion_id"] = str(product["idExpansion"])


def apply_index(rows, language, products, expansions, tcgdex_ids, catalog, set_exp, set_codes=None,
                minimum=MIN_BROWSER_SCAN_EUR, related=None, rules=None, guide=None, names=None):
    """Add index hints to one language queue in place. Returns status counts.

    A variant is priced automatically when Cardmarket can tell it apart: it is
    the only variant of its card with its (reverse, 1st edition) filter key,
    or it is the single plain variant in such a group, or a per-set rule in
    config/cardmarket-variant-version-rules.json maps its kind to a version
    (V1/V2/...). Everything else goes to review as a GROUP (set + kind), so a
    single human rule resolves all cards of that kind in the set.
    names maps card IDs to English names (30th-c reprints, TCGdex ID check).
    """
    set_codes = set_codes or {}
    related = related or {}
    rules = rules or {}
    prefixes = main_prefixes(products)
    by_slug = defaultdict(list)
    for pid, item in products.items():
        by_slug[item["slug"]].append((pid, item))
    # Only fully crawled expansions: a half-read list could make a version
    # look unique although its sibling is on a page not yet read.
    expansions = {k: v for k, v in expansions.items() if v.get("crawledAt")}
    verified_slug = {exp: info["slug"] for exp, info in expansions.items()
                     if info.get("slugVerified") is True and PRODUCT_PATH.fullmatch(str(info.get("slug") or ""))}
    guards = index_set_guards(expansions, set_exp)
    # "<Set>-Additionals" holds the separately sold special prints of a set
    # (e.g. Poke Ball / Master Ball patterns of Prismatic Evolutions).
    additionals = {slug: exp for exp, slug in verified_slug.items() if slug.endswith("-Additionals")}
    siblings = defaultdict(list)
    card_rows = defaultdict(list)
    for row in rows:
        siblings[(row["cardyssey_karte"], filter_key(row))].append(row)
        card_rows[row["cardyssey_karte"]].append(row)
    # 1st edition and unlimited share one Cardmarket product; the price guide
    # mixes them, so every variant of such a card is scanned in the browser
    # (isFirstEd filter) whatever its value.
    first_edition_cards = {r["cardyssey_karte"] for r in rows if filter_key(r)[1] == "Y"}
    stats = Counter()
    for row in rows:
        # Keep an earlier correction: after the first apply the queue already
        # holds the corrected ID, so it would look uncorrected on re-apply.
        earlier_previous = str(row.get("index_previous_id") or "")
        for column in INDEX_COLUMNS:
            row[column] = ""
        cls = variant_class(row)
        kind = kind_key(row)
        group = siblings[(row["cardyssey_karte"], filter_key(row))]
        collision = len(group) > 1
        plain_rows = [r for r in group if not kind_key(r)]
        if collision and not kind and len(plain_rows) > 1:
            # e.g. normal and holo of the same card: no Cardmarket filter.
            kind = "holo-vs-normal"
        if not collision and cls == "SPECIAL":
            cls = "SPECIAL_UNIQUE_FILTER"
        elif collision:
            cls = "COLLISION_" + ("PLAIN" if not kind else "SPECIAL")
        row["variant_class"] = cls
        below = not needs_browser_scan(row, minimum) and row["cardyssey_karte"] not in first_edition_cards
        primary = guards.get(row["set_id"])
        slugs = [verified_slug[str(e)] for e in related.get(row["set_id"], [set_exp.get(row["set_id"])])
                 if str(e) in verified_slug]
        if primary and primary not in slugs:
            slugs.insert(0, primary)
        code = str(set_codes.get(row["set_id"]) or "")
        allowed = ({str(e) for e in related.get(row["set_id"], [])} | {str(set_exp.get(row["set_id"]) or "")}
                   | ({additionals[primary + "-Additionals"]} if primary and primary + "-Additionals" in additionals
                      else set()))
        english = (names or {}).get(row["cardyssey_karte"]) or (row.get("kartenname_suche") if language == "en" else "")

        def tcgdex_pick():
            return _pick_tcgdex_variant(row, card_rows[row["cardyssey_karte"]], catalog, allowed - {""},
                                        english, products, guide, code, prefixes)
        if not slugs:
            alt = tcgdex_pick()
            if alt:
                _set_pick(row, alt, language, catalog, below)
                _finish(row, "DIRECT_PRODUCT_ID_TCGDEX", below, stats)
            else:
                _finish(row, "SET_NOT_INDEXED", below, stats)
            continue
        if row["set_id"] in NAME_MATCH_SETS:
            wanted = normalize_name((names or {}).get(row["cardyssey_karte"]) or row.get("kartenname_suche"))
            matches = sorted((pid, item) for slug in slugs for pid, item in by_slug.get(slug, [])
                             if item.get("reprint") and wanted
                             and normalize_name(item["title"].rsplit(" (", 1)[0]) == wanted)
        else:
            matches = sorted(
                (pid, item) for slug in slugs for pid, item in by_slug.get(slug, [])
                if not item.get("reprint")
                and (title_number_matches(item["title_number"], row["kartennummer"]) if item.get("title_number")
                     else number_matches(item["product"], row["kartennummer"], row["set_id"], code,
                                         prefixes.get(slug))))
        urls = [f"https://www.cardmarket.com/{language}/Pokemon/Products/Singles/{item['slug']}/{item['product']}"
                for _, item in matches]
        main = [m for m in matches if m[1]["slug"] == primary]
        pick, status = None, ""
        rule_kind = kind or "plain"
        rule = rules.get((row["set_id"], rule_kind)) or rules.get(("*", rule_kind))
        if not matches:
            status = "NO_NUMBER_MATCH_IN_SET"
        elif (str(row.get("routing_state") or "") == "VERIFIED_PRODUCT_ID"
              and str(row.get("catalog_singleton_id") or "").isdigit()):
            # A human route only counts with its product ID; a bare
            # "verified" flag without ID would block the index forever.
            status = "HUMAN_ROUTE_KEPT"
        elif not main:
            # Only a secondary expansion (e.g. "Additionals") has this number.
            status = "REVIEW_GROUP"
            row["index_review_group"] = f"{row['set_id']}|{kind or 'plain'}|secondary-expansion"
        elif (collision or len(main) > 1) and rule:
            if rule["action"] == "plain":
                pick = _pick_plain(main, row, language, tcgdex_ids)
            else:
                tagged = [m for m in main if re.search(r"(?:^|-)" + rule["version"] + r"(?:-|$)", m[1]["product"], re.I)]
                pick = tagged[0] if len(tagged) == 1 else None
            status = "DIRECT_PRODUCT_URL_RULE" if pick else "REVIEW_GROUP"
            if not pick:
                row["index_review_group"] = f"{row['set_id']}|{rule_kind}|rule-version-not-found"
        elif collision and kind and kind != "holo-vs-normal" and len(main) == 1:
            # Cardmarket lists ONE product for this number (e.g. Master Ball /
            # Poke Ball patterns in Prismatic Evolutions, Black Bolt, White
            # Flare): the special print is not sold separately there, so no
            # human can pick a product. No Cardmarket price, no review.
            status = "SPECIAL_NOT_SEPARABLE"
            row["index_candidate_urls"] = json.dumps(urls[:1])
        elif collision and (kind or len(plain_rows) != 1):
            pick = _pick_by_variant_ids(row, group, main, guide)
            if pick:
                status = "DIRECT_PRODUCT_URL_VARIANT_ID"
            else:
                status = "REVIEW_GROUP"
                row["index_review_group"] = f"{row['set_id']}|{kind}"
        else:
            pick = _pick_plain(main, row, language, tcgdex_ids)
            if not pick:
                pick = _pick_by_variant_ids(row, group, main, guide)
                status = "DIRECT_PRODUCT_URL_VARIANT_ID" if pick else ""
            if not pick:
                status = "REVIEW_GROUP"
                row["index_review_group"] = f"{row['set_id']}|{rule_kind}|several-versions"
        if not pick and status in ("REVIEW_GROUP", "NO_NUMBER_MATCH_IN_SET", "SPECIAL_NOT_SEPARABLE"):
            alt = tcgdex_pick()
            if alt:
                row["index_review_group"] = ""
                _set_pick(row, alt, language, catalog, below)
                _finish(row, "DIRECT_PRODUCT_ID_TCGDEX", below, stats)
                continue
        if status == "REVIEW_GROUP" or status == "NO_NUMBER_MATCH_IN_SET":
            row["index_candidate_urls"] = json.dumps(urls[:6]) if urls else ""
        if pick:
            pid, item = pick
            current = str(row.get("catalog_singleton_id") or "")
            # Cardmarket's own list (image idProduct + slug number) beats a
            # name-based catalog singleton or a TCGdex ID: same-name cards
            # such as Skyridge Staryu 103/104 were swapped there.
            corrected = bool(current and current != pid)
            if not corrected and earlier_previous and earlier_previous != pid:
                corrected, current = True, earlier_previous
            product = catalog.get(int(pid))
            if not below:
                row["catalog_singleton_id"] = pid
                if product:
                    row["catalog_expansion_id"] = str(product["idExpansion"])
            row["index_product_id"] = pid
            row["index_product_url"] = (f"https://www.cardmarket.com/{language}/Pokemon/Products/Singles/"
                                        f"{item['slug']}/{item['product']}")
            if not status:
                status = "DIRECT_PRODUCT_URL_ID_CORRECTED" if corrected else "DIRECT_PRODUCT_URL"
            if corrected:
                row["index_previous_id"] = current
        _finish(row, status, below, stats)
    return stats
