#!/usr/bin/env python3
"""Admin monitor for the eBay sold scanner (read only, no eBay requests).

Reads the Windows collector files (status, state, queue, log, results) and the
database, and prints one JSON snapshot: is it running, where is it, pages and
matched sales per hour, today's page budget, and what ended up as a value.
"""
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/EbaySold')
IMPORT_LOG = Path('/home/tv/cardshop/logs/ebay-sold.log')  # written by the cron job in the live repo
DAILY_CAP = 1500          # Ebay-Sold-Collector.ps1 -DailyCap default
PAGES_PER_RUN = 70        # Ebay-Sold-Collector.ps1 -MaxPages default
TAIL_BYTES = 6_000_000
HOURS = 24
LOG_LINE = re.compile(r'^(\S+)\s+(START|END|ALERT|STOP|ERROR)\b\s*(.*)$')


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default


def parse_time(value):
    try:
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except ValueError:
        return None


def tail_lines(path, size):
    try:
        with open(path, 'rb') as f:
            f.seek(0, 2)
            end = f.tell()
            f.seek(max(0, end - size))
            data = f.read()
    except OSError:
        return []
    lines = data.decode('utf-8-sig', errors='replace').splitlines()
    return lines[1:] if end > size else lines


def psql(sql):
    try:
        out = subprocess.run(['docker', 'exec', 'cardyssey-db', 'psql', '-X', '-q', '-U', 'cardyssey',
                              '-d', 'cardyssey', '-At', '-c', sql],
                             capture_output=True, text=True, timeout=15, check=True).stdout
        return out.strip()
    except (OSError, subprocess.SubprocessError):
        return ''


def collector_runs(now):
    runs, current = [], None
    for line in tail_lines(BASE / 'ebay-sold-collector.log', 200_000):
        m = LOG_LINE.match(line.strip().lstrip('﻿'))
        if not m:
            continue
        at, kind, rest = parse_time(m.group(1)), m.group(2), m.group(3)
        if not at:
            continue
        if kind == 'START':
            current = {'start': at.isoformat(), 'end': None, 'status': 'LÄUFT', 'pages': None}
            runs.append(current)
        elif kind == 'END' and current:
            parts = rest.split()
            current['end'] = at.isoformat()
            current['status'] = parts[0] if parts else 'END'
            pages = re.search(r'pages=(\d+)', rest)
            current['pages'] = int(pages.group(1)) if pages else None
            current = None
    # A START older than an hour without END was cut off (sleep, restart, ...).
    for r in runs:
        if r['end'] is None and now - parse_time(r['start']) > timedelta(minutes=65):
            r['status'] = 'OHNE_ENDE'
    return runs[-12:]


def main():
    now = datetime.now(timezone.utc)
    status = read_json(BASE / 'ebay-sold-status.json', {}) or {}
    state = read_json(BASE / 'ebay-sold-state.json', {}) or {}
    queue = read_json(BASE / 'ebay-sold-queue.json', []) or []
    if isinstance(queue, dict):
        queue = [queue]
    done = set(state.get('done') or [])
    runs = collector_runs(now)
    last_run = runs[-1] if runs else None

    # Pages and hits per hour from the results file.
    since = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=HOURS - 1)
    hours = {since + timedelta(hours=i): {'pages': 0, 'items': 0} for i in range(HOURS)}
    last_page = None
    for line in tail_lines(BASE / 'ebay-sold-results.jsonl', TAIL_BYTES):
        try:
            page = json.loads(line.strip().lstrip('﻿'))
        except ValueError:
            continue
        at = parse_time(page.get('at'))
        if not at:
            continue
        last_page = {'query': page.get('query'), 'at': at.isoformat(), 'hits': len(page.get('items') or [])}
        bucket = at.replace(minute=0, second=0, microsecond=0)
        if bucket in hours:
            hours[bucket]['pages'] += 1
            hours[bucket]['items'] += sum(1 for i in page.get('items') or [] if i.get('title') != 'Shop on eBay')

    # Matched sales per hour come from the database (first time a sale was saved).
    matched = Counter()
    for row in psql(f"""SELECT date_trunc('hour', first_collected_at AT TIME ZONE 'UTC'), count(*)
                        FROM ebay_sold_history WHERE first_collected_at >= '{since.isoformat()}'
                        GROUP BY 1""").splitlines():
        h, n = row.split('|')
        matched[datetime.fromisoformat(h).replace(tzinfo=timezone.utc)] = int(n)
    hour_list = [{'hour': h.isoformat(), 'pages': v['pages'], 'items': v['items'], 'sales': matched.get(h, 0)}
                 for h, v in sorted(hours.items())]

    totals = {}
    row = psql("""SELECT count(*), count(DISTINCT (language_code, card_id)),
                         count(*) FILTER (WHERE first_collected_at >= now() - interval '24 hours'),
                         min(sold_on), max(sold_on)
                  FROM ebay_sold_history""")
    if row:
        a, b, c, d, e = row.split('|')
        totals = {'sales': int(a), 'cards': int(b), 'sales24h': int(c), 'oldestSale': d or None, 'newestSale': e or None}
    row = psql("""SELECT count(*), max(updated_at) FROM ebay_price_cache WHERE source='CARDYSSEY_EBAY'""")
    if row:
        a, b = row.split('|')
        totals.update({'variantsValued': int(a), 'valuesUpdatedAt': b or None})
    row = psql("""SELECT count(*), coalesce(sum(items_seen),0), coalesce(sum(sales_matched),0)
                  FROM ebay_sold_checks WHERE checked_at >= now() - interval '24 hours'""")
    if row:
        a, b, c = row.split('|')
        totals.update({'cardsChecked24h': int(a), 'itemsSeen24h': int(b), 'salesMatched24h': int(c)})

    recent = []
    for line in psql("""SELECT json_build_object('title', h.title, 'eur', h.sold_eur, 'soldOn', h.sold_on,
                               'lang', h.language_code, 'url', h.listing_url, 'savedAt', h.first_collected_at)
                        FROM ebay_sold_history h WHERE h.title <> '' ORDER BY h.sold_on DESC, h.first_collected_at DESC LIMIT 8""").splitlines():
        try:
            recent.append(json.loads(line))
        except ValueError:
            pass

    plan = {}
    for line in reversed(tail_lines(IMPORT_LOG, 20_000)):
        try:
            last = json.loads(line)
        except ValueError:
            continue
        plan = {'due': (last.get('plan') or {}).get('due'), 'lastImport': last.get('import')}
        break
    try:
        plan['importAt'] = datetime.fromtimestamp(IMPORT_LOG.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        pass

    status_at = parse_time(status.get('updated_at'))
    running = bool(last_run and last_run['status'] == 'LÄUFT')
    problem = str(status.get('status') or '') not in ('', 'OK', 'DAILY_CAP', 'NO_QUEUE')
    stale = not running and (status_at is None or now - status_at > timedelta(hours=2))
    if problem:
        health = 'PROBLEM'
    elif running:
        health = 'LÄUFT'
    elif stale:
        health = 'STEHT'
    else:
        health = 'WARTET'

    print(json.dumps({
        'checkedAt': now.isoformat(),
        'health': health,
        'collectorStatus': status.get('status'),
        'collectorStatusAt': status_at.isoformat() if status_at else None,
        'current': last_page,
        'today': {'pages': int(state.get('pages') or 0), 'cap': DAILY_CAP, 'perRun': PAGES_PER_RUN},
        'queue': {'size': len(queue), 'done': len([q for q in queue if isinstance(q, dict) and q.get('key') in done]),
                  'due': plan.get('due')},
        'runs': runs,
        'hours': hour_list,
        'totals': totals,
        'import': plan,
        'recent': recent,
    }, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
