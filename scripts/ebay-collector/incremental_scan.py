"""Persistent per-card eBay scan cursors; updates only after complete successful fetch.

A cursor is the time the completed sold-listing search was collected, *not*
the most recent sale date. A two-day overlap mitigates delayed indexing.
"""
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import json
from price_history import db,sql

OVERLAP_DAYS=2

def since_date(last_success,overlap_days=OVERLAP_DAYS):
    when=datetime.fromisoformat(str(last_success).replace('Z','+00:00'))
    if when.tzinfo is None:when=when.replace(tzinfo=timezone.utc)
    return (when.astimezone(timezone.utc).date()-timedelta(days=overlap_days)).isoformat()

def saved_baseline(card_id,query,run_root):
    """Recover a scan cursor from fully fetched existing set-run evidence.

    The first weekly run can use recent full-scan reports without retrieving
    previously scanned pages again. Incomplete runs are never a baseline.
    """
    root=Path(run_root)
    candidates=[root/card_id/'sales.json']
    for p in root.parent.glob(root.name+'-history-*'):
        candidates.append(p/card_id/'sales.json')
    for p in root.parent.glob(root.name+'-pre-*'):
        candidates.append(p/card_id/'sales.json')
    best=None
    for path in candidates:
        try:
            report=json.loads(path.read_text())
            config=report.get('config',{})
            if config.get('query')!=query or config.get('language')!='de':continue
            # Older legacy scans used a 30-day cutoff and are not a safe
            # baseline for the new full-history collector.
            if int(config.get('max_age_days') or 0)<36500:continue
            pages=report.get('pages') or []
            if not pages or any(x.get('status')!='OK' for x in pages):continue
            when=datetime.fromisoformat(report['collected_at'].replace('Z','+00:00'))
            if when.tzinfo is None:when=when.replace(tzinfo=timezone.utc)
            if when>datetime.now(timezone.utc):continue
            if best is None or when>best:best=when
        except (OSError,ValueError,KeyError,TypeError):pass
    return best

def read_cursor(card_id,query):
    result=db('SELECT last_success_at FROM ebay_scan_checkpoint WHERE card_id='+sql(card_id)+
              " AND language_code='de' AND search_query="+sql(query)+';')
    return result.strip() or None

def mark_success(card_id,query,completed_at=None):
    completed_at=completed_at or datetime.now(timezone.utc)
    stamp=completed_at.isoformat()
    db('''INSERT INTO ebay_scan_checkpoint(card_id,language_code,search_query,last_success_at)
      VALUES('''+sql(card_id)+",'de',"+sql(query)+','+sql(stamp)+'''::timestamptz)
      ON CONFLICT(card_id,language_code) DO UPDATE SET
      search_query=EXCLUDED.search_query,last_success_at=GREATEST(
      CASE WHEN ebay_scan_checkpoint.search_query=EXCLUDED.search_query
      THEN ebay_scan_checkpoint.last_success_at ELSE EXCLUDED.last_success_at END,
      EXCLUDED.last_success_at);''')


def scan_window(card_id,query,run_root):
    cursor=read_cursor(card_id,query)
    if cursor:return since_date(cursor),'DATABASE',datetime.fromisoformat(cursor.replace('Z','+00:00'))
    old=saved_baseline(card_id,query,run_root)
    if old:return since_date(old),'PREVIOUS_COMPLETE_REPORT',old
    return None,'INITIAL_SCAN',None
