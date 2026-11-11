#!/usr/bin/env python3
"""Read-only, bounded DE/EN Cardmarket collector status for authenticated admin UI."""
import argparse
import csv
import json
import importlib.util
from decimal import Decimal,InvalidOperation
from datetime import datetime,timezone
from collections import Counter
from pathlib import Path

BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
PROBLEMS={'ERROR','NO_EXACT_NUMBER_SEARCH_HIT','PRODUCT_SET_SLUG_MISMATCH','MULTIPLE_SEARCH_HITS','NO_PRODUCT_ID','PRODUCT_ID_NOT_IN_VERIFIED_SET','FILTER_UNAVAILABLE','FILTER_NOT_APPLIED','FILTER_UNVERIFIED_EMPTY','DEFERRED_SOCKET','DEFERRED_PROVIDER_TIMEOUT','NO_CONFIRMED_FILTERED_OFFERS'}

def feed_only_covered(row):
    """Mirror the non-destructive browser gate in the Windows collector."""
    if row.get('scan_tier')!='4' or row.get('needs_price')!='NO':return False
    if str(row.get('manual_scan_requested_at') or ''):return False
    if str(row.get('foil') or '') or str(row.get('sonderdruck') or ''):return False
    if str(row.get('stempel') or '') not in ('','[]','null'):return False
    if not row.get('existing_source'):return False
    try:return Decimal(str(row.get('existing_price_eur') or '0'))>0
    except InvalidOperation:return False

def snapshot(base:Path,language:str):
    if language not in ('de','en'):raise ValueError('unsupported language')
    queue=base/f'queue-{language}.csv'
    with queue.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    expected={(r['cardyssey_karte'],r['variante_id']) for r in rows}
    # Same eligibility policy as the live scanner: the 31k priced ordinary
    # bulk cards remain in the catalog and price feeds, not browser work.
    feed_only={(r['cardyssey_karte'],r['variante_id']) for r in rows if feed_only_covered(r)}
    browser=expected-feed_only
    completed={}
    events=base/f'browser-observations-{language}.jsonl'
    if events.exists():
        with events.open(encoding='utf-8-sig') as f:
            for line in f:
                try:x=json.loads(line)
                except (ValueError,TypeError):continue
                k=(x.get('card_id'),x.get('variant_id'))
                if k in browser:completed[k]=x
    scanned={key:r for key,r in completed.items() if r.get('status') not in ('STARTED','ERROR','DEFERRED_SOCKET','DEFERRED_PROVIDER_TIMEOUT')}
    pending=[x for x in completed.values() if x.get('status') in PROBLEMS or str(x.get('status','')).startswith('DEFERRED')]
    progress_path=base/f'progress-{language}.json'
    progress={}
    if progress_path.exists():
        try:progress=json.loads(progress_path.read_text(encoding='utf-8-sig'))
        except ValueError:pass
    session={}
    session_path=base/'browser-session-status.json'
    if session_path.exists():
        try:
            raw=json.loads(session_path.read_text(encoding='utf-8-sig'))
            session={k:raw.get(k) for k in ('status','reason','login','checkedAt','profileExists')}
        except (ValueError,OSError):pass
    rescan_epoch=None
    rescan_done=None
    epoch_file=base/'full-rescan-epoch.json'
    if epoch_file.exists():
        from datetime import datetime,timezone
        try:
            epoch=json.loads(epoch_file.read_text(encoding='utf-8-sig'))
            rescan_epoch=datetime.fromisoformat(epoch['requestedAt'].replace('Z','+00:00'))
            if rescan_epoch.tzinfo is None:rescan_epoch=rescan_epoch.replace(tzinfo=timezone.utc)
            rescan_done=sum(bool(x.get('seen_at')) and datetime.fromisoformat(str(x['seen_at']).replace('Z','+00:00'))>=rescan_epoch
                and str(x.get('status','')) not in ('STARTED','BLOCKED','LOGIN_REQUIRED','ERROR')
                and not str(x.get('status','')).startswith('DEFERRED') for x in completed.values())
        except (OSError,ValueError,TypeError):rescan_epoch=None;rescan_done=None
    total=len(expected);done=len(scanned)
    matched=sum(bool(r.get('identity_confirmed')) for r in completed.values())
    search_misses=sum(r.get('status')=='NO_EXACT_NUMBER_SEARCH_HIT' for r in completed.values())
    priced=sum(r.get('needs_price')=='NO' and r.get('existing_price_eur') not in ('',None) for r in rows)
    missing=sum(r.get('needs_price')=='YES' for r in rows)
    eligible_missing=sum(r.get('needs_price')=='YES' and str(r.get('scan_tier'))!='4' for r in rows)
    bulk_missing=sum(r.get('needs_price')=='YES' and str(r.get('scan_tier'))=='4' for r in rows)
    raw_status=str(progress.get('status') or 'NOT_STARTED')
    stalled=False
    if raw_status=='RUNNING' and progress.get('updated_at'):
        try:
            last=datetime.fromisoformat(str(progress['updated_at']).replace('Z','+00:00'))
            if last.tzinfo is None:last=last.replace(tzinfo=timezone.utc)
            stalled=(datetime.now(timezone.utc)-last).total_seconds()>300
        except ValueError:pass
    current_problems=sum(bool(x.get('seen_at')) and rescan_epoch is not None
         and str(x['seen_at'])[:19]>=rescan_epoch.isoformat()[:19]
         and (x.get('status') in PROBLEMS or str(x.get('status','')).startswith('DEFERRED'))
         for x in completed.values())
    # Surface missing vs non-filterable fields as proactive data guidance.
    spec=importlib.util.spec_from_file_location('cardmarket_filter_readiness',Path(__file__).with_name('cardmarket-filter-readiness.py'))
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    readiness=[audit.analyze(row) for row in rows]
    missing_filter_inputs=sum(bool(x['missing']) for x in readiness)
    nonfilterable_specials=sum(bool(x['unsupported']) for x in readiness)
    return {'language':language,'totalVariants':total,'uniqueCards':len({r['cardyssey_karte'] for r in rows}),
       'browserTotal':len(browser),'rescanStartedAt':rescan_epoch.isoformat() if rescan_epoch else None,'rescanProcessed':rescan_done,'feedOnly':len(feed_only),'browserObserved':len(completed),
       'browserProcessed':done,'productMapped':matched,'noExactSearchMatch':search_misses,
       'pricedVariants':priced,'missingVariants':missing,'browserMissingPriority':eligible_missing,'feedMissingPriority':bulk_missing,
       'browserRemaining':max(0,len(browser)-done),
       'missingFilterInputs':missing_filter_inputs,'nonfilterableSpecialPrints':nonfilterable_specials,
       'progressPercent':round(done/len(browser)*100,2) if browser else 100,
       'totalReviewedPercent':round((total-len(browser)+done)/total*100,2) if total else 100,
       'status':'RUNNING_STALLED' if stalled else raw_status,
       'problemCountCurrentCycle':current_problems,
       'browserSession':session,
       'lastCard':str(progress.get('last_card') or ''),'updatedAt':progress.get('updated_at'),
       'problemCountInObserved':len(pending),
       'recentProblems':[{'cardId':x.get('card_id'),'variantId':x.get('variant_id'),'status':x.get('status'),
          'setId':x.get('set_id'),'detail':str(x.get('error') or x.get('pagination_failure') or '')[:160]}
          for x in reversed(pending[-8:])],
       'recentEvents':[{'cardId':x.get('card_id'),'status':x.get('status'),'at':x.get('seen_at')} for x in list(completed.values())[-6:][::-1]]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--language',choices=('de','en'),default='de');a=p.parse_args()
    try:print(json.dumps(snapshot(BASE,a.language),ensure_ascii=False))
    except (OSError,ValueError) as e:print(json.dumps({'error':'scan_data_unavailable','detail':str(e)[:100]}));raise SystemExit(2)
