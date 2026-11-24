#!/usr/bin/env python3
"""DE/EN prices come ONLY from Cardmarket.

1. Publish: every DE/EN variant with our own verified Cardmarket product ID
   (Cardmarket expansion list or a human-confirmed route) gets Cardmarket's
   official price-guide value, unchanged: price trend (reverse prints: the
   "-holo" fields), fallback avg30 -> avg7 -> avg -> low. No multipliers.
   Exact browser prices (language, NM) younger than 30 days are kept.
2. Clean: every other DE/EN price (TCGdex copies, TCGplayer, CardTrader, ...)
   is saved to a backup file and removed. A variant without a Cardmarket price
   has no price rather than a non-Cardmarket one (owner decision 24.11.2026).
3. All DE/EN rows get next_attempt_at far in the future, so the API's price
   worker (TCGdex & co.) never fills or refreshes DE/EN again.

The guide is skipped where it is ambiguous: cards with a 1st edition print
(1st edition and unlimited share one product; the browser scans them exactly)
and two variants of one card on the same product (same reverse flag).
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
SOURCE = 'CARDMARKET_GUIDE'
BROWSER = ('CARDMARKET_DE_NM_WEB', 'CARDMARKET_EN_NM_WEB', 'CARDMARKET_WEB')
# Cardmarket values with an own product mapping (old official refresh, Chinese identity crosswalk).
CARDMARKET = (SOURCE, 'CARDMARKET_OFFICIAL', 'CARDMARKET_OFFICIAL_CT_IDENTITY') + BROWSER
KEEP_MANUAL = ('MANUAL', 'ADMIN')
BROWSER_FRESH_DAYS = 30
NEVER = "TIMESTAMPTZ '2100-01-01'"
KEYS = ('trend', 'avg30', 'avg7', 'avg', 'low')
CLEANED_DETAIL = 'DE/EN: nur Cardmarket-Preise (keine andere Quelle)'


def psql(sql=None, stdin=None):
    cmd = ['docker', 'exec', '-i', 'cardyssey-db', 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-U', 'cardyssey',
           '-d', 'cardyssey', '-At'] + (['-c', sql] if sql else [])
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True, check=True).stdout


def lit(value):
    return "'" + str(value).replace("'", "''") + "'"


def is_cardmarket(source):
    return source in CARDMARKET


def is_manual(source):
    return source.upper().startswith(KEEP_MANUAL)


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


def plan(queue, guides, prices, now):
    """-> (updates, keep_browser, stats). Pure function, no database access."""
    fresh_cut = (now - timedelta(days=BROWSER_FRESH_DAYS)).isoformat()
    first_ed = first_edition_cards(queue)
    resolved = {key: mapped_product(row) for key, row in queue.items()}
    shared = defaultdict(int)
    for key, pid in resolved.items():
        if pid:
            row = queue[key]
            shared[(row['cardyssey_karte'], pid, is_reverse(row))] += 1
    stats = defaultdict(int)
    updates, keep = [], []
    for key, row in queue.items():
        cur = prices.get(key) or {}
        source = cur.get('source') or ''
        if source in BROWSER and str(cur.get('updated') or '') >= fresh_cut and (cur.get('eur') or 0) > 0:
            keep.append(key)
            stats['keep_browser_exact'] += 1
            continue
        if is_manual(source):
            stats['keep_manual'] += 1
            continue
        pid = resolved[key]
        if not pid:
            stats['no_verified_product_id'] += 1
            continue
        if row['cardyssey_karte'] in first_ed:
            stats['first_edition_browser_only'] += 1
            continue
        if shared[(row['cardyssey_karte'], pid, is_reverse(row))] > 1:
            stats['variants_share_one_product'] += 1
            continue
        value, key_used = guide_value(guides.get(pid, {}), is_reverse(row))
        if not value:
            stats['no_guide_value'] += 1
            continue
        stats['publish'] += 1
        updates.append({'card': row['cardyssey_karte'], 'variant': row['variante_id'], 'price': value,
                        'detail': f'Cardmarket product {pid}; key {key_used}',
                        'old': cur.get('eur'), 'old_source': source, 'set': row['set_id'],
                        'name': row.get('kartenname_suche') or '', 'key': key_used,
                        'url': row.get('index_product_url') or row.get('known_url') or str(pid)})
    return updates, keep, dict(stats)


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
SELECT card,{lang},variant,legacy_variant,{source},price,'PRICE_FOUND',detail,NOW(),{never}
FROM legacy WHERE legacy_variant IS NOT NULL
ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET
 legacy_variant=EXCLUDED.legacy_variant, source=EXCLUDED.source, base_eur=EXCLUDED.base_eur,
 resolution_status='PRICE_FOUND', failure_detail=EXCLUDED.failure_detail, updated_at=NOW(),
 next_attempt_at=EXCLUDED.next_attempt_at
WHERE NOT (upper(COALESCE(tcg_price_cache.source,'')) LIKE 'MANUAL%' OR upper(COALESCE(tcg_price_cache.source,'')) LIKE 'ADMIN%')
  AND NOT (tcg_price_cache.source = ANY(ARRAY[{browser}]) AND COALESCE(tcg_price_cache.base_eur,0) > 0
           AND tcg_price_cache.updated_at >= NOW() - INTERVAL '{fresh} days');
"""

# Remove every DE/EN price that is not from Cardmarket (or manual); block the
# API worker for all DE/EN rows; drop guide values whose mapping is gone.
CLEAN = """
UPDATE tcg_price_cache SET source=NULL, base_eur=NULL, resolution_status='NO_PRICE',
       failure_detail={detail}, updated_at=NOW(), next_attempt_at={never}
WHERE language_code={lang} AND COALESCE(base_eur,0) > 0
  AND NOT (COALESCE(source,'') = ANY(ARRAY[{cardmarket}]))
  AND NOT (upper(COALESCE(source,'')) LIKE 'MANUAL%' OR upper(COALESCE(source,'')) LIKE 'ADMIN%');
UPDATE tcg_price_cache SET source=NULL, base_eur=NULL, resolution_status='NO_PRICE',
       failure_detail='Cardmarket-Zuordnung nicht mehr eindeutig', updated_at=NOW(), next_attempt_at={never}
WHERE language_code={lang} AND source={source}
  AND NOT (card_id||'|'||variant_id = ANY(ARRAY[{published}]::text[]));
UPDATE tcg_price_cache SET next_attempt_at={never}
WHERE language_code={lang} AND (next_attempt_at IS NULL OR next_attempt_at < NOW() + INTERVAL '50 years');
"""


def write(language, updates, published_keys):
    browser = ','.join(lit(s) for s in BROWSER)
    for i in range(0, len(updates), 500):
        payload = lit(json.dumps([{k: u[k] for k in ('card', 'variant', 'price', 'detail')}
                                  for u in updates[i:i + 500]], ensure_ascii=False))
        psql(stdin='BEGIN;\n' + UPSERT.format(payload=payload, lang=lit(language), source=lit(SOURCE),
                                              browser=browser, fresh=BROWSER_FRESH_DAYS, never=NEVER) + '\nCOMMIT;')
    psql(stdin='BEGIN;\n' + CLEAN.format(lang=lit(language), detail=lit(CLEANED_DETAIL), never=NEVER,
                                         cardmarket=','.join(lit(s) for s in CARDMARKET), source=lit(SOURCE),
                                         published=','.join(lit(k) for k in sorted(published_keys)) or "''")
         + '\nCOMMIT;')


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
    report = {'checkedAt': now.isoformat(), 'guideDate': created, 'mode': 'apply' if a.apply else 'dry-run'}
    changes = []
    for language in ('de', 'en'):
        with open(a.base / f'queue-{language}.csv', encoding='utf-8-sig', newline='') as f:
            queue = {f"{r['cardyssey_karte']}|{r['variante_id']}": r for r in csv.DictReader(f)}
        if len(queue) < 10000:
            raise SystemExit(f'queue-{language}.csv incomplete ({len(queue)} rows)')
        prices = current_prices(language)
        updates, keep, stats = plan(queue, guides, prices, now)
        by_key = {f"{u['card']}|{u['variant']}": u for u in updates}
        # Rows that will lose their price: non-Cardmarket sources, or guide
        # rows whose verified mapping is gone.
        removed = [o for k, o in prices.items() if (o.get('eur') or 0) > 0 and k not in by_key
                   and not is_manual(o['source'])
                   and (not is_cardmarket(o['source']) or o['source'] == SOURCE)]
        stats['removed_non_cardmarket'] = sum(1 for o in removed if o['source'] != SOURCE)
        stats['removed_unmapped_guide'] = sum(1 for o in removed if o['source'] == SOURCE)
        report[language] = stats
        if a.apply:
            BACKUPS.mkdir(parents=True, exist_ok=True)
            changed = [prices[k] for k, u in by_key.items() if k in prices
                       and (prices[k].get('source') != SOURCE or abs(float(prices[k].get('eur') or 0) - u['price']) >= 0.005)]
            if changed or removed:
                with open(BACKUPS / f'before-{language}-{stamp}.jsonl', 'w', encoding='utf-8') as f:
                    for old in changed + removed:
                        f.write(json.dumps(old, ensure_ascii=False, default=str) + '\n')
            for old_file in BACKUPS.glob(f'before-{language}-*.jsonl'):
                if old_file.stat().st_mtime < now.timestamp() - 14 * 86400:
                    old_file.unlink()
            write(language, updates, by_key.keys())
        for u in updates:
            old = u['old']
            if old is not None and u['old_source'] == SOURCE and abs(float(old) - u['price']) < 0.005:
                continue
            changes.append([language, u['set'], u['card'], u['variant'], u['name'], u['old_source'],
                            '' if old is None else f'{float(old):.2f}', f"{u['price']:.2f}",
                            '' if not old else f"{(u['price'] - float(old)) / float(old) * 100:+.0f}",
                            u['key'], u['url']])
        for o in removed:
            card, variant = o['k'].split('|', 1)
            row = queue.get(o['k'], {})
            changes.append([language, row.get('set_id', ''), card, variant, row.get('kartenname_suche', ''),
                            o['source'], f"{float(o['eur']):.2f}", '', 'entfernt', '', ''])
    changes.sort(key=lambda c: -abs(float(c[7] or 0) - float(c[6] or 0)))
    (ROOT / 'reports').mkdir(exist_ok=True)
    # Keep the last list that really changed prices (a quiet run must not
    # replace it with an empty file).
    if changes:
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
