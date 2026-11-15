"""Card-only links backed by an original set and collector number."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from cardmarket_game_profile import load_game_profile

ROOT = Path(__file__).resolve().parents[3]
FEEDS = Path('/home/tv/.local/state/cardyssey-queue/price-feeds')
CONFIG = json.loads((ROOT/'config/cardmarket-stamp-routes.json').read_text(encoding='utf-8'))
SET_SLUGS = json.loads((ROOT/'config/cardmarket-set-url-guards.json').read_text(encoding='utf-8'))
VINTAGE_EXPANSIONS = {'base1':'1523', 'base2':'1525', 'base3':'1526'}
VINTAGE_EVIDENCE = 'VINTAGE_MAIN_SET_PAGE_PRINT_UNVERIFIED'
SUBSET_EVIDENCE = 'STAMP_SUBSET_SET_NUMBER_CANDIDATES'
PATH = re.compile(r'^/(de|en)/Pokemon/Products/Singles/([A-Za-z0-9-]+)/([A-Za-z0-9-]+)$')


def official_products():
    name = hashlib.sha256(load_game_profile()['product_url'].encode()).hexdigest() + '.json'
    raw = json.loads((FEEDS/name).read_text(encoding='utf-8'))
    return {str(row['idProduct']): row for row in raw['products']}, raw.get('createdAt')


def token(text):
    return re.sub(r'[\s_]+','-',str(text or '').strip().casefold())


def read_list(value):
    try:
        result = json.loads(value or '[]')
    except (ValueError, TypeError):
        return []
    return result if isinstance(result,list) else []


def stamp_route(row):
    stamps = {token(s) for s in read_list(row.get('stempel'))}
    sid = row.get('set_id') or ''
    routes = [
        ('TRICK_OR_TRADE', bool(stamps & {'trick-or-trade','pumpkin-pikachu'})),
        ('PROFESSOR_PROGRAM', bool(stamps & {'professorenprogramm','professor-program'})),
        ('PRIZE_PACK', bool(re.match(r'^(?:sv|me)(?:[0-9]|[ep]$)',sid)
                           and stamps & {'player-rewards-program','set-logo'})),
        ('WORLD_CHAMPIONSHIPS', bool(re.match(r'^(?:base|ecard|ex|dp|pl|hgss|bw)',sid)
                                   and stamps.intersection(CONFIG['worldChampionshipStamps']))),
    ]
    matched = [name for name, enabled in routes if enabled]
    return matched[0] if len(matched) == 1 else 'AMBIGUOUS_STAMP_ROUTE' if matched else ''


def vintage_subtype(row):
    return row.get('set_id') in VINTAGE_EXPANSIONS and token(row.get('sonderdruck')) in {
        'copyright-1999-2000','1999-2000-copyright','missing-expansion-symbol',
        'fehlendes-erweiterungssymbol','shadowless','schattenlos',
    }


def product_path(url):
    if not isinstance(url,str):
        return None
    try:
        parsed = urlsplit(url)
    except (TypeError, ValueError):
        return None
    if parsed.scheme != 'https' or parsed.netloc != 'www.cardmarket.com':
        return None
    return PATH.fullmatch(parsed.path)


def subset_urls(row, urls, language, route):
    sid = row.get('set_id') or ''
    code = CONFIG['setCodes'].get(sid)
    number = re.fullmatch(r'(?:[A-Za-z]{1,12})?(\d{1,4})',str(row.get('kartennummer') or ''))
    if not code or not number or route == 'AMBIGUOUS_STAMP_ROUTE':
        return []
    code = re.escape(code)
    ranked = {}
    for url in urls:
        path = product_path(url)
        if not path:
            continue
        slug, product = path[2], path[3]
        prefix = None
        priority = 2
        if route == 'TRICK_OR_TRADE' and (year := re.fullmatch(r'Trick-or-Trade-20(\d\d)',slug)):
            prefix = 'BOO' + year[1] + code
        elif route == 'PROFESSOR_PROGRAM' and slug == 'Professor-Program':
            prefix = 'PPP' + code
        elif route == 'PRIZE_PACK':
            if slug.startswith('Play-Pokemon-Prize-Pack-Series-'):
                prefix = r'PPS\d{1,2}' + code
            elif SET_SLUGS.get(sid) and slug == SET_SLUGS[sid]+'-Additionals':
                prefix, priority = 'x'+code, 1
        elif route == 'WORLD_CHAMPIONSHIPS' and (year := re.fullmatch(r'WCD-20(\d\d)',slug)):
            prefix = 'WCD'+year[1]+code
        if prefix and (tail := re.search(r'(?:^|-)'+prefix+r'-?(\d{1,4})$',product,re.I)):
            if int(tail[1]) == int(number[1]):
                ranked[f'https://www.cardmarket.com/{language}/Pokemon/Products/Singles/{slug}/{product}'] = priority
    return sorted(ranked,key=lambda url:(-ranked[url],url))


def observations(base, language):
    path = base/f'browser-observations-{language}.jsonl'
    if path.is_file():
        with path.open(encoding='utf-8-sig') as stream:
            for line in stream:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry,dict):
                    yield entry


def product_ids(row):
    return {pid.strip() for field in ('cardmarket_ids','set_card_candidate_ids','catalog_singleton_id')
            for pid in (row.get(field) or '').split(',') if pid.strip().isdigit()}


def vintage_page_index(queues, logs, products):
    ids = defaultdict(set)
    pages = defaultdict(set)
    by_family = defaultdict(set)
    for pid, product in products.items():
        expansion = str(product.get('idExpansion') or '')
        family = str(product.get('idMetacard') or '')
        if expansion in VINTAGE_EXPANSIONS.values() and family and family != '0':
            by_family[(expansion,family)].add(pid)

    def key_for(row):
        return row['cardyssey_karte'], row.get('kartennummer') or ''

    def add_page(row, url, pid):
        sid = row['set_id']
        path = product_path(url)
        number = key_for(row)[1]
        if not number.isdecimal() or not path or path[2] != SET_SLUGS[sid]:
            return
        if not re.search(r'-'+CONFIG['setCodes'][sid]+r'0*'+str(int(number))+r'$',path[3],re.I):
            return
        version = re.search(r'(?:^|-)V(\d+)(?:-|$)',path[3],re.I)
        if version and version[1] != '1':
            return
        pages[key_for(row)].add((path[2],path[3],pid))

    for locale, rows in queues.items():
        original = {}
        for row in rows:
            sid = row['set_id']
            if sid not in VINTAGE_EXPANSIONS:
                continue
            expansion = VINTAGE_EXPANSIONS[sid]
            matched = {pid for pid in product_ids(row)
                       if str(products.get(pid,{}).get('idExpansion')) == expansion}
            # Fossil non-holo collector numbers can have the holo ID in old
            # input files. Allow siblings within the same official expansion
            # only as candidates. The live URL must still prove the number.
            related = matched.union(*(by_family[(expansion,str(products[pid].get('idMetacard') or ''))]
                                      for pid in matched))
            ids[key_for(row)].update(related)
            original[(row['cardyssey_karte'],row['variante_id'])] = (row,related)
            if len(matched) == 1 and (row.get('cardmarket_ids') or '').strip() in matched and row.get('known_url'):
                add_page(row,row['known_url'],next(iter(matched)))
        for row, _ in original.values():
            seed = CONFIG.get('knownVintagePages',{}).get(row['cardyssey_karte'],{})
            if seed.get('productId') in ids[key_for(row)]:
                add_page(row,seed.get('url'),seed['productId'])
        for entry in logs[locale]:
            key = (entry.get('card_id'),entry.get('variant_id'))
            if key not in original or entry.get('card_number_url_verified') is not True:
                continue
            row, matched = original[key]
            pid = str(entry.get('product_id') or '')
            if pid in matched:
                add_page(row,entry.get('url') or '',pid)
    return ids, pages


def route_evidence(row, language, observed, vintage_index):
    route = stamp_route(row)
    vintage = vintage_subtype(row)
    evidence = {'stamp_route':route, 'reference_candidate_urls':'',
                'reference_product_url':'', 'reference_product_id':'',
                'vintage_card_candidate_ids':'',
                'exact_print_filter_supported':'false' if vintage or route else ''}
    if row.get('routing_state') == 'VERIFIED_PRODUCT_ID':
        return evidence
    if vintage:
        key = (row['cardyssey_karte'], row.get('kartennummer') or '')
        ids,pages = vintage_index
        evidence['vintage_card_candidate_ids'] = ','.join(sorted(ids.get(key,())))
        candidates = pages.get(key,())
        if len(candidates) == 1:
            slug, product, pid = next(iter(candidates))
            evidence['reference_product_url'] = f'https://www.cardmarket.com/{language}/Pokemon/Products/Singles/{slug}/{product}'
            evidence['reference_product_id'] = pid
    elif route:
        known = CONFIG.get('knownPages',{}).get(row['cardyssey_karte'],{}).get(route,())
        found = subset_urls(row,[*observed,*known],language,route)
        if found:
            evidence['reference_candidate_urls'] = json.dumps(found[:5],separators=(',',':'))
    return evidence


def reference_urls(row, language):
    route = stamp_route(row)
    if route:
        return subset_urls(row,read_list(row.get('reference_candidate_urls')),language,route)
    if row.get('reference_evidence') == VINTAGE_EVIDENCE and vintage_subtype(row):
        url = row.get('reference_product_url') or ''
        path = product_path(url)
        if path and path[1] == language and path[2] == SET_SLUGS[row['set_id']]:
            return [url]
    return []


def load_evidence(base, queues, products=None):
    logs = {lang:list(observations(base,lang)) for lang in queues}
    if products is None and any(vintage_subtype(r) for rows in queues.values() for r in rows):
        products,_ = official_products()
    vintage_index = vintage_page_index(queues,logs,products or {})
    result = {}
    links = defaultdict(set)
    for lang, rows in queues.items():
        stamped = {(r['cardyssey_karte'],r['variante_id']) for r in rows if stamp_route(r)}
        for entry in logs[lang]:
            key = (entry.get('card_id'),entry.get('variant_id'))
            if key in stamped:
                links[key].update(u for u in (entry.get('score_top_candidate_urls') or []) if isinstance(u,str))
                if isinstance(entry.get('url'),str):
                    links[key].add(entry['url'])
    for lang, rows in queues.items():
        result[lang] = {
            (r['cardyssey_karte'],r['variante_id']):route_evidence(
                r,lang,links[(r['cardyssey_karte'],r['variante_id'])],vintage_index)
            for r in rows if vintage_subtype(r) or stamp_route(r)
        }
    return result


def read_queue(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))
