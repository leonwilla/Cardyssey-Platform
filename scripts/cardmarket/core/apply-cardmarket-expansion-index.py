#!/usr/bin/env python3
"""Apply the crawled Cardmarket expansion index to the DE/EN browser queues.

Adds direct product URLs (no search needed) for standard prints, and offline
review candidates for special prints. Also writes index-set-url-guards.json
(set -> expansion slug proven by official product IDs on the list pages).
No provider requests, no prices, no database writes.
"""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root = _cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0, str(_cm_import))
import argparse
import csv
import fcntl
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from cardmarket_game_profile import load_game_profile
from price_feed_client import fetch_json
import cardmarket_expansion_index as idx

BASE = Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
ROOT = Path(__file__).resolve().parents[3]


def rewrite_queue(path, language, mutate):
    lock = path.with_name(f'queue-{language}.review.lock')
    with lock.open('a') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            fields = list(reader.fieldnames or [])
            rows = list(reader)
        if not rows or 'cardyssey_karte' not in fields:
            raise RuntimeError('invalid queue ' + str(path))
        result = mutate(rows)
        fields += [c for c in idx.INDEX_COLUMNS if c not in fields]
        tmp = path.with_suffix(path.suffix + '.index.tmp')
        try:
            with tmp.open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            # Windows keeps the CSV locked while a collector reads it.
            for attempt in range(40):
                try:
                    os.replace(tmp, path)
                    break
                except PermissionError:
                    if attempt == 39:
                        raise
                    time.sleep(15)
        finally:
            tmp.unlink(missing_ok=True)
        return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, default=BASE)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    index_file = args.base / 'cardmarket-expansion-index.json'
    if not index_file.is_file():
        print(json.dumps({'status': 'NO_INDEX_YET'}))
        return
    products_file = args.base / 'cardmarket-expansion-index-products.jsonl'
    lines = products_file.read_text(encoding='utf-8-sig').splitlines() if products_file.is_file() else []
    expansions, products = idx.load_index(json.loads(index_file.read_text(encoding='utf-8-sig')), lines)
    catalog = {x['idProduct']: x for x in fetch_json(load_game_profile()['product_url'])['products']}
    tcgdex = idx.load_tcgdex_product_ids()
    votes = idx.set_expansion_votes(tcgdex, catalog)
    set_exp = idx.set_expansions(tcgdex, catalog, votes)
    related = idx.related_expansions(tcgdex, catalog, votes)
    set_codes = json.loads((ROOT / 'config/cardmarket-stamp-routes.json').read_text(encoding='utf-8')).get('setCodes') or {}
    guards = idx.index_set_guards(expansions, set_exp)
    rules_file = ROOT / 'config/cardmarket-variant-version-rules.json'
    rules = idx.load_rules(json.loads(rules_file.read_text(encoding='utf-8'))) if rules_file.is_file() else {}
    review = {}
    report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'indexedProducts': len(products),
              'verifiedExpansions': sum(1 for e in expansions.values() if e.get('slugVerified') is True),
              'setGuards': len(guards)}
    for language in ('de', 'en'):
        path = args.base / f'queue-{language}.csv'

        def mutate(rows, language=language):
            stats = idx.apply_index(rows, language, products, expansions, tcgdex, catalog, set_exp, set_codes,
                                    related=related, rules=rules)
            for r in rows:
                if r.get('index_status') == 'REVIEW_GROUP' and r.get('index_review_group'):
                    g = review.setdefault(r['index_review_group'], {'de': 0, 'en': 0, 'examples': [], 'urls': set()})
                    g[language] += 1
                    if len(g['examples']) < 5:
                        g['examples'].append(f"{r['cardyssey_karte']} {r['kartenname_suche']} ({r['drucktyp']})")
                    g['urls'].update(json.loads(r['index_candidate_urls'] or '[]')[:3])
            return stats
        if args.dry_run:
            with path.open(encoding='utf-8-sig', newline='') as stream:
                report[language] = dict(mutate(list(csv.DictReader(stream))))
        else:
            report[language] = dict(rewrite_queue(path, language, mutate))
    if not args.dry_run:
        out = args.base / 'index-set-url-guards.json'
        tmp = out.with_suffix('.tmp')
        tmp.write_text(json.dumps({'schema': 1, 'source': 'CARDMARKET_EXPANSION_LIST_OFFICIAL_PRODUCT_IDS',
                                   'setSlugs': guards}, ensure_ascii=False, indent=1), encoding='utf-8')
        os.replace(tmp, out)
        (ROOT / 'reports').mkdir(exist_ok=True)
        with (ROOT / 'reports/cardmarket-variant-review-groups.csv').open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(['gruppe', 'set', 'variantenart', 'varianten_de', 'varianten_en', 'beispiele',
                        'cardmarket_kandidaten', 'regel_vorlage'])
            for key, g in sorted(review.items(), key=lambda kv: -(kv[1]['de'] + kv[1]['en'])):
                set_id, kind = key.split('|')[:2]
                w.writerow([key, set_id, kind, g['de'], g['en'], ' | '.join(g['examples']),
                            ' '.join(sorted(g['urls'])[:6]),
                            json.dumps({'set': set_id, 'kind': kind, 'action': 'version', 'version': 'V?'})])
        report['reviewGroups'] = len(review)
        (ROOT / 'reports/cardmarket-expansion-index-apply.json').write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
