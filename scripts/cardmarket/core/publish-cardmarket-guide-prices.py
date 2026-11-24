#!/usr/bin/env python3
"""Daily DE/EN prices from the official Cardmarket price guide.

The value is Cardmarket's own number for the product, unchanged: price trend
(fallback avg30 -> avg7 -> avg -> low; reverse prints use the "-holo"
fields). No multipliers, no estimates. The guide is the same for every
language; exact language prices come from the browser scan of valuable cards.

* Product ID: only our own verified mapping (Cardmarket expansion list or a
  human-confirmed route). Never TCGdex IDs.
* Never overwrites: exact browser prices younger than 30 days, verified
  TCGplayer routes, CardTrader or other manual sources.
* Skipped: special prints without an own Cardmarket product, and cards with a
  1st edition print (the guide mixes 1st edition and unlimited sales).
* With --apply the touched rows are saved first (rollback), and a change
  report is written. Rows get next_attempt_at = now + 3 days, so the API's
  Sunday TCGdex refresh does not overwrite them while this job runs daily.
"""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root = _cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root / 'cardmarket/core'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0, str(_cm_import))
import argparse
import csv
import json
import math
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cardmarket_expansion_index import FIRST_EDITION
from cardmarket_game_profile import load_game_profile
from price_feed_client import fetch_json

BASE = Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
ROOT = Path(__file__).resolve().parents[3]
BACKUPS = Path('/home/tv/cardyssey-backups/cardmarket-guide-prices')
SOURCE = {'de': 'CARDMARKET_GUIDE', 'en': 'CARDMARKET_GUIDE'}
BROWSER = {'CARDMARKET_DE_NM_WEB', 'CARDMARKET_EN_NM_WEB', 'CARDMARKET_WEB'}
# Indirect copies of the same guide (often with TCGdex product IDs) or no source.
REPLACEABLE = {'', 'TCGDEX', 'TCGDEX_CATALOG', 'TCGDEX_SHARED', 'TCGDEX_FAMILY', 'TCGDEX_SHARED_HOLO',
               'TCGDEX_CATALOG_CACHE', 'TCGDEX_TCGPLAYER', 'POKEMONTCGIO_CARDMARKET', 'CARDMARKET_OFFICIAL',
               'CARDMARKET_GUIDE'}
BROWSER_FRESH_DAYS = 30
KEYS = ('trend', 'avg30', 'avg7', 'avg', 'low')


def psql(sql=None, stdin=None):
    cmd = ['docker', 'exec', '-i', 'cardyssey-db', 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-U', 'cardyssey',
           '-d', 'cardyssey', '-At'] + (['-c', sql] if sql else [])
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True, check=True).stdout


def guide_value(guide, reverse):
    suffix = '-holo' if reverse else ''
    for key in KEYS:
        v = guide.get(key + suffix)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0:
            return round(float(v), 2), key + suffix
    return None, None


def mapped_product(row):
    """Our own verified Cardmarket product ID for a queue row, or None."""
    status = row.get('index_status') or ''
    match = row.get('index_match') or ''
    if status.startswith('DIRECT_') or (status == 'GUIDE_PRICE_BELOW_THRESHOLD' and match.startswith('DIRECT_')):
        pid = row.get('index_product_id') or ''
    elif row.get('routing_state') == 'VERIFIED_PRODUCT_ID':
        pid = row.get('catalog_singleton_id') or ''
    else:
        return None
    return int(pid) if pid.isdigit() else None


def guide_safe(row):
    """Plain prints, or a special print resolved to its own product by a rule."""
    if 'DIRECT_PRODUCT_URL_RULE' in (row.get('index_status'), row.get('index_match')):
        return True
    return (row.get('variant_class') or 'STANDARD') == 'STANDARD'


def is_reverse(row):
    return str(row.get('drucktyp') or '').strip().lower() == 'reverse'


def first_edition_cards(queue):
    return {r['cardyssey_karte'] for r in queue.values()
            if r.get('variant_class') == 'FIRST_EDITION'
            or FIRST_EDITION.search(str(r.get('stempel') or '')) or FIRST_EDITION.search(str(r.get('sonderdruck') or ''))}


def current_prices(language):
    sql = (f"SELECT json_build_object('k',card_id||'|'||variant_id,'source',coalesce(source,''),'eur',base_eur,"
           f"'updated',updated_at,'status',resolution_status,'detail',failure_detail,'next',next_attempt_at,"
           f"'legacy',legacy_variant)::text FROM tcg_price_cache WHERE language_code='{language}'")
    return {o['k']: o for o in map(json.loads, filter(None, psql(sql).splitlines()))}


def verified_other_routes(language):
    sql = (f"SELECT card_id||'|'||variant_id FROM price_source_routing WHERE language_code='{language}' "
           f"AND primary_provider<>'CARDMARKET' AND verification_state='VERIFIED_PRODUCT_ID'")
    return set(filter(None, psql(sql).splitlines()))


def plan(queue, guides, prices, routes, now):
    fresh_cut = (now - timedelta(days=BROWSER_FRESH_DAYS)).isoformat()
    first_ed = first_edition_cards(queue)
    stats = defaultdict(int)
    updates, protect = [], []
    for key, row in queue.items():
        cur = prices.get(key)
        source = (cur or {}).get('source') or ''
        if source in BROWSER and str(cur.get('updated') or '') >= fresh_cut:
            protect.append(key)
            stats['keep_browser_exact'] += 1
            continue
        if key in routes:
            stats['keep_verified_other_route'] += 1
            continue
        if cur and source not in REPLACEABLE and source not in BROWSER:
            stats['keep_other_source:' + source] += 1
            continue
        pid = mapped_product(row)
        if not pid:
            stats['no_verified_product_id'] += 1
            continue
        if not guide_safe(row):
            stats['special_print_not_in_guide'] += 1
            continue
        if row['cardyssey_karte'] in first_ed:
            stats['first_edition_mixed_in_guide'] += 1
            continue
        value, key_used = guide_value(guides.get(pid, {}), is_reverse(row))
        if not value:
            stats['no_guide_value'] += 1
            continue
        stats['publish'] += 1
        updates.append({'card': row['cardyssey_karte'], 'variant': row['variante_id'], 'price': value,
                        'detail': f'Cardmarket product {pid}; key {key_used}',
                        'old': (cur or {}).get('eur'), 'old_source': source, 'set': row['set_id'],
                        'name': row.get('kartenname_suche') or '', 'key': key_used, 'product': pid,
                        'url': row.get('index_product_url') or row.get('known_url') or ''})
    return updates, protect, dict(stats)


UPSERT = """
WITH payload AS (
 SELECT x->>'card' AS card, x->>'variant' AS variant, (x->>'price')::numeric AS price, x->>'detail' AS detail
 FROM jsonb_array_elements({payload}::jsonb) x
), legacy AS (
 SELECT p.*, COALESCE(cached.legacy_variant, v.value->>'legacyVariant') AS legacy_variant
 FROM payload p
 LEFT JOIN tcg_price_cache cached ON cached.language_code={lang} AND cached.card_id=p.card AND cached.variant_id=p.variant
 LEFT JOIN catalog_cards_mirror c ON c.language_code={lang} AND c.card_id=p.card AND cached.card_id IS NULL
 LEFT JOIN LATERAL (SELECT value FROM jsonb_array_elements(c.variants) value WHERE value->>'id'=p.variant LIMIT 1) v ON TRUE
)
INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,source,base_eur,resolution_status,
                            failure_detail,updated_at,next_attempt_at)
SELECT card,{lang},variant,legacy_variant,{source},price,'PRICE_FOUND',detail,NOW(),NOW()+INTERVAL '3 days'
FROM legacy WHERE legacy_variant IS NOT NULL
ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET
 legacy_variant=EXCLUDED.legacy_variant, source=EXCLUDED.source, base_eur=EXCLUDED.base_eur,
 resolution_status='PRICE_FOUND', failure_detail=EXCLUDED.failure_detail, updated_at=NOW(),
 next_attempt_at=EXCLUDED.next_attempt_at
WHERE COALESCE(tcg_price_cache.source,'') = ANY(ARRAY[{replaceable}])
   OR (tcg_price_cache.source = ANY(ARRAY[{browser}]) AND tcg_price_cache.updated_at < NOW() - INTERVAL '{fresh} days');
"""

PROTECT = """
UPDATE tcg_price_cache t SET next_attempt_at=GREATEST(COALESCE(t.next_attempt_at,NOW()),NOW()+INTERVAL '3 days')
FROM jsonb_array_elements({payload}::jsonb) x
WHERE t.language_code={lang} AND t.card_id=x->>'card' AND t.variant_id=x->>'variant'
  AND t.source = ANY(ARRAY[{browser}]);
"""


def lit(value):
    return "'" + str(value).replace("'", "''") + "'"


def write(language, updates, protect):
    replaceable = ','.join(lit(s) for s in sorted(REPLACEABLE))
    browser = ','.join(lit(s) for s in sorted(BROWSER))
    for i in range(0, len(updates), 500):
        payload = lit(json.dumps([{k: u[k] for k in ('card', 'variant', 'price', 'detail')}
                                  for u in updates[i:i + 500]], ensure_ascii=False))
        psql(stdin='BEGIN;\n' + UPSERT.format(payload=payload, lang=lit(language), source=lit(SOURCE[language]),
                                              replaceable=replaceable, browser=browser,
                                              fresh=BROWSER_FRESH_DAYS) + '\nCOMMIT;')
    keys = [{'card': k.split('|', 1)[0], 'variant': k.split('|', 1)[1]} for k in protect]
    for i in range(0, len(keys), 1000):
        psql(stdin=PROTECT.format(payload=lit(json.dumps(keys[i:i + 1000])), lang=lit(language), browser=browser))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true')
    p.add_argument('--base', type=Path, default=BASE)
    a = p.parse_args()
    now = datetime.now(timezone.utc)
    guide = fetch_json(load_game_profile()['price_url'], max_age=20 * 3600)
    guides = {int(x['idProduct']): x for x in guide.get('priceGuides') or []}
    if len(guides) < 50000:
        raise SystemExit('price guide incomplete')
    stamp = now.strftime('%Y%m%d-%H%M%S')
    created = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', str(guide.get('createdAt') or ''))
    report = {'checkedAt': now.isoformat(), 'guideDate': created,
              'mode': 'apply' if a.apply else 'dry-run'}
    changes = []
    for language in ('de', 'en'):
        with open(a.base / f'queue-{language}.csv', encoding='utf-8-sig', newline='') as f:
            queue = {f"{r['cardyssey_karte']}|{r['variante_id']}": r for r in csv.DictReader(f)}
        prices = current_prices(language)
        updates, protect, stats = plan(queue, guides, prices, verified_other_routes(language), now)
        report[language] = stats
        if a.apply:
            BACKUPS.mkdir(parents=True, exist_ok=True)
            with open(BACKUPS / f'before-{language}-{stamp}.jsonl', 'w', encoding='utf-8') as f:
                for u in updates:
                    old = prices.get(f"{u['card']}|{u['variant']}")
                    if old:
                        f.write(json.dumps(old, ensure_ascii=False, default=str) + '\n')
            write(language, updates, protect)
        for u in updates:
            old = u['old']
            if old is not None and abs(float(old) - u['price']) < 0.005:
                continue
            changes.append([language, u['set'], u['card'], u['variant'], u['name'], u['old_source'],
                            '' if old is None else f'{float(old):.2f}', f"{u['price']:.2f}",
                            '' if not old else f"{(u['price'] - float(old)) / float(old) * 100:+.0f}",
                            u['key'], u['url'] or str(u['product'])])
    changes.sort(key=lambda c: -abs(float(c[7]) - float(c[6] or 0)))
    (ROOT / 'reports').mkdir(exist_ok=True)
    with open(ROOT / 'reports/cardmarket-guide-price-changes.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['sprache', 'set', 'karte', 'variante', 'name', 'alte_quelle', 'alter_preis', 'neuer_preis',
                    'aenderung_prozent', 'cardmarket_wert', 'cardmarket_produkt'])
        w.writerows(changes)
    report['changedRows'] = len(changes)
    (ROOT / 'reports/cardmarket-guide-prices-latest.json').write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
