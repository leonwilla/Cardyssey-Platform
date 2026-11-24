#!/usr/bin/env python3
"""Admin monitor for the expansion-index scan (read only, no provider requests).

Shows speed per hour, index crawl progress, rescan backlog, variant review
groups and the Cloudflare clearance state. `--review-groups-csv` prints the
grouped review list for download instead.
"""
import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
ROOT = Path(__file__).resolve().parents[3]
CACHE = Path.home() / '.cache/cardyssey-index-monitor-backlog.json'
# Measured 19.11.2026 00:00 - 24.11.2026 09:50 UTC, before the switch to the
# expansion index (search based scan, both languages together).
BASELINE = {'window': '19.–24.11.2026 (alte Suche)', 'pagesPerHour': 12.3, 'pricesPerHour': 2.7}
SWITCHED_AT = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)  # expansion index live
TAIL_BYTES = 4_000_000


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default


def parse_time(value):
    try:
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def tail_observations(path, max_bytes=TAIL_BYTES):
    try:
        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            data = f.read().decode('utf-8', 'replace')
    except OSError:
        return []
    out = []
    for line in data.splitlines()[1:] if size > max_bytes else data.splitlines():
        try:
            out.append(json.loads(line.lstrip('﻿')))
        except ValueError:
            pass
    return out


def speed(observations, now, hours=12):
    """Per-hour buckets for the last `hours` hours (both languages); the
    average uses only full hours since the switch to the expansion index."""
    start = max(now - timedelta(hours=hours), SWITCHED_AT)
    buckets = {}
    for o in observations:
        t = parse_time(o.get('seen_at'))
        if not t or t < start:
            continue
        b = buckets.setdefault(t.strftime('%Y-%m-%dT%H:00Z'), Counter())
        if o.get('product_load_mode'):
            b['pages'] += 1
        status = str(o.get('status') or '')
        if status.startswith('COMPLETE'):
            b['prices'] += 1
        if status == 'BLOCKED':
            b['blocks'] += 1
        if o.get('lookup_strategy') == 'EXPANSION_INDEX_DIRECT_V1':
            b['indexDirect'] += 1
    # Every hour counts, also hours without any result (e.g. fully blocked).
    hour = start.replace(minute=0, second=0, microsecond=0)
    while hour <= now:
        buckets.setdefault(hour.strftime('%Y-%m-%dT%H:00Z'), Counter())
        hour += timedelta(hours=1)
    rows = [{'hour': k, **{f: v.get(f, 0) for f in ('pages', 'prices', 'blocks', 'indexDirect')}}
            for k, v in sorted(buckets.items())]
    full = [r for r in rows if r['hour'] != now.strftime('%Y-%m-%dT%H:00Z')]
    span = len(full) or 1
    return {'hours': rows,
            'pagesPerHour': round(sum(r['pages'] for r in full) / span, 1),
            'pricesPerHour': round(sum(r['prices'] for r in full) / span, 1),
            'blocks': sum(r['blocks'] for r in rows)}


def index_progress(base):
    state = read_json(base / 'cardmarket-expansion-index.json', {}) or {}
    plan = read_json(base / 'expansion-index-plan.json', {}) or {}
    exps = state.get('expansions') or {}
    statuses = Counter(str(e.get('status') or 'PENDING') for e in exps.values())
    targets = plan.get('expansions') or plan.get('targets') or []
    planned = len(targets) if isinstance(targets, (list, dict)) else 0
    pages_total = sum(int(t.get('maxPages') or 0) for t in (targets.values() if isinstance(targets, dict) else targets)
                      if isinstance(t, dict))
    pages_done = sum(int(e.get('pagesDone') or 0) for e in exps.values())
    complete = sum(1 for e in exps.values() if e.get('crawledAt'))
    last = read_json(base / 'expansion-index-status.json', {}) or {}
    return {'plannedExpansions': planned, 'completeExpansions': complete,
            'pagesDone': pages_done, 'pagesPlanned': pages_total,
            'statuses': dict(statuses), 'lastRun': last}


def backlog(base, max_age=300):
    """Cases still waiting for their first scan via a direct URL (cached)."""
    cached = read_json(CACHE)
    if cached and time.time() - cached.get('at', 0) < max_age:
        return cached['data']
    data = {}
    for lang in ('de', 'en'):
        latest = {}
        try:
            with open(base / f'browser-observations-{lang}.jsonl', encoding='utf-8-sig') as f:
                for line in f:
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    if o.get('key'):
                        latest[o['key']] = o
            with open(base / f'queue-{lang}.csv', encoding='utf-8-sig', newline='') as f:
                rows = list(csv.DictReader(f))
        except OSError:
            continue
        c = Counter()
        for r in rows:
            st = r.get('index_status') or ''
            c['status:' + (st or 'NONE')] += 1
            c['total'] += 1
            if r.get('index_product_url') or (r.get('routing_state') == 'VERIFIED_PRODUCT_ID' and r.get('known_url')):
                c['withUrl'] += 1
            if not st.startswith('DIRECT_'):
                continue
            p = latest.get(f"{r['cardyssey_karte']}|{r['variante_id']}")
            if not p:
                c['neverScanned'] += 1
            elif p.get('lookup_strategy') == 'EXPANSION_INDEX_DIRECT_V1':
                c['doneViaIndex'] += 1
            else:
                same = urlsplit(p.get('url') or '').path.lower() == urlsplit(r.get('index_product_url') or '').path.lower()
                if same and str(p.get('status') or '').startswith('COMPLETE'):
                    c['alreadyComplete'] += 1
                elif st == 'DIRECT_PRODUCT_URL_ID_CORRECTED' or str(p.get('status') or '').startswith('COMPLETE'):
                    c['rescanCorrected'] += 1
                else:
                    c['rescanFailed'] += 1
        data[lang] = dict(c)
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps({'at': time.time(), 'data': data}))
    except OSError:
        pass
    return data


def review_groups(root, limit=15):
    path = root / 'reports/cardmarket-variant-review-groups.csv'
    try:
        with path.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f, delimiter=';'))
    except OSError:
        return {'total': 0, 'variants': 0, 'top': []}
    def n(v):
        try:
            return int(v or 0)
        except ValueError:
            return 0
    return {'total': len(rows), 'variants': sum(n(r['varianten_de']) + n(r['varianten_en']) for r in rows),
            'top': [{'group': r['gruppe'], 'set': r['set'], 'kind': r['variantenart'], 'de': n(r['varianten_de']),
                     'en': n(r['varianten_en']), 'examples': r['beispiele'][:200]} for r in rows[:limit]]}


def clearance(base, observations):
    seen = read_json(base / 'telegram-block-first-seen.json')
    session = read_json(base / 'browser-session-status.json', {}) or {}
    blocks = sorted(str(o.get('seen_at')) for o in observations if o.get('status') == 'BLOCKED' and o.get('seen_at'))
    return {'session': session.get('status'), 'login': session.get('login'),
            'fingerprintAvailable': bool(session.get('clearanceId')),
            'waitingSince': (seen or {}).get('firstSeen'), 'lastBlockAt': blocks[-1] if blocks else None,
            'note': 'Cardmarket lässt die Cloudflare-Freigabe nach etwa 60 Minuten ablaufen.'}


def imports(root):
    out = {}
    for lang in ('de', 'en'):
        try:
            last = (root / f'logs/cardmarket-verified-prices-{lang}.log').read_text(encoding='utf-8').strip().splitlines()[-1]
            out[lang] = json.loads(last)
        except (OSError, IndexError, ValueError):
            out[lang] = None
    return out


def snapshot(base=BASE, root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    obs = tail_observations(base / 'browser-observations-de.jsonl') + tail_observations(base / 'browser-observations-en.jsonl')
    index = index_progress(base)
    queued = backlog(base)
    # A one-time full rescan makes sense once every set list is read and the
    # old failed / corrected cases went through their direct-URL rescan.
    lists_done = index['plannedExpansions'] > 0 and (
        index['completeExpansions'] + index['statuses'].get('SLUG_NOT_FOUND', 0) >= index['plannedExpansions'])
    open_rescans = sum(b.get('rescanFailed', 0) + b.get('rescanCorrected', 0) for b in queued.values())
    ready = {'ready': lists_done and open_rescans == 0, 'setListsComplete': lists_done, 'openRescans': open_rescans}
    return {'checkedAt': now.isoformat(), 'baseline': BASELINE, 'speed': speed(obs, now), 'fullRescan': ready,
            'index': index, 'backlog': queued, 'reviewGroups': review_groups(root),
            'apply': read_json(root / 'reports/cardmarket-expansion-index-apply.json'),
            'guidePrices': read_json(root / 'reports/cardmarket-guide-prices-latest.json'),
            'clearance': clearance(base, obs), 'imports': imports(root)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--review-groups-csv', action='store_true')
    p.add_argument('--guide-changes-csv', action='store_true')
    a = p.parse_args()
    if a.review_groups_csv or a.guide_changes_csv:
        name = 'cardmarket-variant-review-groups.csv' if a.review_groups_csv else 'cardmarket-guide-price-changes.csv'
        sys.stdout.write((ROOT / 'reports' / name).read_text(encoding='utf-8-sig'))
        return
    print(json.dumps(snapshot(), ensure_ascii=False))


if __name__ == '__main__':
    main()
