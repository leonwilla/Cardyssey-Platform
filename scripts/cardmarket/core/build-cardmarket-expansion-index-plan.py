#!/usr/bin/env python3
"""Plan the Cardmarket expansion-list crawl (read only, no provider requests).

Writes expansion-index-plan.json for Cardmarket-Expansion-Index.ps1: which
expansions contain cards that need a language-exact browser price, their
candidate URL slugs and the official product IDs used to verify a slug.
"""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root = _cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0, str(_cm_import))
import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from cardmarket_game_profile import load_game_profile
from price_feed_client import fetch_json
import cardmarket_expansion_index as idx

BASE = Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')


def read_queue(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def known_guards(base):
    guards = {}
    observed = base / 'observed-set-url-guards.json'
    if observed.is_file():
        data = json.loads(observed.read_text(encoding='utf-8-sig'))
        guards.update({k: v.get('setSlug') for k, v in (data.get('setSlugs') or {}).items() if v.get('setSlug')})
    verified = base / 'verified-set-url-guards.json'
    if verified.is_file():
        guards.update(json.loads(verified.read_text(encoding='utf-8-sig')))
    return guards


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, default=BASE)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    out = args.output or args.base / 'expansion-index-plan.json'
    catalog = {x['idProduct']: x for x in fetch_json(load_game_profile()['product_url'])['products']}
    queues = {lang: read_queue(args.base / f'queue-{lang}.csv') for lang in ('de', 'en')}
    overview_file = args.base / 'cardmarket-expansions-overview.json'
    overview = []
    if overview_file.is_file():
        overview = json.loads(overview_file.read_text(encoding='utf-8-sig')).get('expansions') or []
    plan = idx.build_plan(queues, idx.load_tcgdex_product_ids(), catalog, overview,
                          idx.load_set_names(), known_guards(args.base))
    plan['createdAt'] = datetime.now(timezone.utc).isoformat()
    plan['overviewAvailable'] = bool(overview)
    tmp = out.with_suffix('.tmp')
    tmp.write_text(json.dumps(plan, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, out)
    print(json.dumps({'output': str(out), **plan['summary'], 'overviewAvailable': bool(overview)}))


if __name__ == '__main__':
    main()
