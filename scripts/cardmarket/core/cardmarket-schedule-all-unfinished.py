#!/usr/bin/env python3
"""One-time non-destructive full-epoch recovery of failed or partial Cardmarket cards.

The existing full-rescan epoch already queues historical and never-scanned rows.
Only current-epoch failures need manual_scan_requested_at to become due again.
Do not requeue complete asking medians or catalog-only bulk mapping.
"""
from __future__ import annotations
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse,csv,fcntl,json,os,tempfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
REPORT=Path('/home/tv/cardshop/reports/cardmarket-review')
COMPLETED={
 'MAPPED_NO_PRICE_REQUIRED','COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED',
 'COMPLETE_FILTERED_ASKING_MEDIAN','SOURCE_ONLY','SUCCESS',
}
# Explicitly include incomplete listings, multiple search hits, unresolved
# products, missing-number hits, and transient provider/browser failures.
RETRYABLE={
 'MULTIPLE_SEARCH_HITS','NO_EXACT_NUMBER_SEARCH_HIT',
 'PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED','PRODUCT_ID_NOT_VERIFIED_FOR_CARD',
 'PRODUCT_ID_NOT_IN_VERIFIED_SET','PRODUCT_SET_SLUG_MISMATCH','NO_PRODUCT_ID',
 'SET_MAPPING_PENDING','FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE',
 'NO_CONFIRMED_FILTERED_OFFERS','FILTER_UNAVAILABLE','FILTER_UNVERIFIED_EMPTY',
 'FILTER_NOT_APPLIED','DEFERRED_PROVIDER_TIMEOUT','DEFERRED_SOCKET',
 'DEFERRED_SEARCH_RESULTS_UNVERIFIED','BLOCKED','LOGIN_REQUIRED','ERROR',
 'PROVIDER_ERROR','PROVIDER_TIMEOUT','CONNECTION_LOST',
 'MISSING_REQUIRED_SCAN_FIELDS',
}
def parse(value):
    try:
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError,ValueError):return None

def audit_and_schedule(base=BASE, apply=False, languages=('de','en'), now=None):
    epoch_data=json.loads((base/'full-rescan-epoch.json').read_text(encoding='utf-8-sig'))
    epoch=parse(epoch_data['requestedAt'])
    if not epoch:raise ValueError('invalid epoch')
    stamp=now or datetime.now(timezone.utc)
    if stamp<=epoch:raise ValueError('invalid scheduling time')
    report={'existingEpoch':epoch.isoformat(),'requestedAt':stamp.isoformat(),
            'mode':'SCHEDULED' if apply else 'DRY_RUN','languages':{}}
    for lang in languages:
        if lang not in ('de','en'):raise ValueError('Invalid language')
        latest={}
        with (base/f'browser-observations-{lang}.jsonl').open(encoding='utf-8-sig') as f:
            for line in f:
                try:
                    x=json.loads(line);key=(x['card_id'],x['variant_id'])
                    if x.get('status'):latest[key]=x
                except (TypeError,ValueError,KeyError):continue
        queue=base/f'queue-{lang}.csv'
        counts=Counter();retries=Counter();sample=[];to_mark=set()
        # Lock prevents conflicting bulk retry writers; atomically replace
        # queue so a running scanner continues with its already-loaded batch.
        with (base/f'queue-{lang}.review.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            with queue.open(encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f);fields=list(reader.fieldnames or []);rows=list(reader)
            if 'manual_scan_requested_at' not in fields:
                raise ValueError('Existing queue missing manual_scan_requested_at')
            for row in rows:
                key=(row['cardyssey_karte'],row['variante_id'])
                obs=latest.get(key)
                if not obs:
                    counts['never_scanned_already_due']+=1;continue
                seen=parse(obs.get('seen_at'))
                if not seen or seen<epoch:
                    counts['historical_only_already_due']+=1;continue
                status=str(obs['status'])
                if status in COMPLETED:
                    counts['completed_untouched']+=1;continue
                if status in RETRYABLE:
                    retries[status]+=1;to_mark.add(key)
                    if len(sample)<20:sample.append({'cardId':key[0],'variantId':key[1],'status':status})
                else:counts['unknown_status_for_manual_review']+=1
            if apply and to_mark:
                for row in rows:
                    if (row['cardyssey_karte'],row['variante_id']) in to_mark:
                        previous=parse(row.get('manual_scan_requested_at'))
                        if previous and previous>stamp:continue
                        row['manual_scan_requested_at']=stamp.isoformat()
                fd,tmp=tempfile.mkstemp(prefix=f'recovery-{lang}-',suffix='.csv',dir=base)
                try:
                    with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as f:
                        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
                    os.replace(tmp,queue)
                finally:
                    if os.path.exists(tmp):os.unlink(tmp)
        report['languages'][lang]={'totalQueue':len(rows),
           'requeuedCurrentFailures':len(to_mark),
           'failureStatuses':dict(retries),
           'unscannedAlreadyDue':counts['never_scanned_already_due'],
           'historicalAlreadyDue':counts['historical_only_already_due'],
           'completedUnchanged':counts['completed_untouched'],
           'unknownStatusesForReview':counts['unknown_status_for_manual_review'],
           'sample':sample}
    if apply:
        REPORT.mkdir(parents=True,exist_ok=True)
        path=REPORT/'all-unfinished-recovery-20261110.json'
        path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        report['reportFile']=str(path)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--apply',action='store_true')
    p.add_argument('--languages',choices=['de','en','both'],default='both')
    a=p.parse_args()
    result=audit_and_schedule(apply=a.apply,
            languages=('de','en') if a.languages=='both' else (a.languages,))
    print(json.dumps(result,ensure_ascii=False))
