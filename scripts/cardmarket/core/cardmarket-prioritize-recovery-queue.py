#!/usr/bin/env python3
"""Reorder *existing* Cardmarket recovery queues without losing a single variant.

Priority:
  0  open metacard candidates requiring a specific print check
  1  independently human-confirmed special-print routes
  2  manually queued special prints
  3  other failed special prints
  4  other special prints
  5  manually requested non-special failures
  6  remaining technical / mapping errors
  7  ordinary non-bulk (current-epoch incomplete)
  8  bulk (has feed fallback; not deleted)
The scanner applies its own due/epoch gate, so this only changes order, not
whether a card should be scanned. No price/cache/identity DB writes.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse,csv,fcntl,json,os,re,subprocess,tempfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
FAILED={'MULTIPLE_SEARCH_HITS','NO_EXACT_NUMBER_SEARCH_HIT','PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED',
'PRODUCT_ID_NOT_VERIFIED_FOR_CARD','PRODUCT_ID_NOT_IN_VERIFIED_SET','PRODUCT_SET_SLUG_MISMATCH',
'NO_PRODUCT_ID','SET_MAPPING_PENDING','FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE',
'NO_CONFIRMED_FILTERED_OFFERS','FILTER_UNAVAILABLE','FILTER_UNVERIFIED_EMPTY',
'FILTER_NOT_APPLIED','DEFERRED_PROVIDER_TIMEOUT','DEFERRED_SOCKET',
'DEFERRED_SEARCH_RESULTS_UNVERIFIED','BLOCKED','LOGIN_REQUIRED','ERROR',
'PROVIDER_ERROR','PROVIDER_TIMEOUT','CONNECTION_LOST','MISSING_REQUIRED_SCAN_FIELDS'}
def moment(value):
    try:
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError,TypeError):return None
def is_special(row):
    stamp=str(row.get('stempel') or '').strip()
    return bool(str(row.get('foil') or '').strip() or
        str(row.get('sonderdruck') or '').strip() or
        stamp not in ('','[]','null') or
        str(row.get('drucktyp') or '').lower().strip() not in ('normal','reverse'))
def is_pending_manually(row, obs):
    request=moment(row.get('manual_scan_requested_at'))
    previous=moment(obs.get('seen_at')) if obs else None
    return bool(request and (not previous or request>previous))
def classify(row, obs, known_key=False):
    special=is_special(row)
    manual=is_pending_manually(row,obs)
    failed=bool(obs and str(obs.get('status') or '') in FAILED)
    verified=str(row.get('routing_state') or '')=='VERIFIED_PRODUCT_ID'
    if known_key:return 0
    if verified and special:return 1
    if special and manual:return 2
    if special and failed:return 3
    if special:return 4
    if manual:return 5
    if failed:return 6
    if str(row.get('scan_tier') or '')!='4':return 7
    return 8

def prioritize(rows:list,latest:dict,manual_candidates:set)->tuple[list,dict]:
    items=[]
    for i,row in enumerate(rows):
        key=(row['cardyssey_karte'],row['variante_id'])
        rank=classify(row,latest.get(key),key in manual_candidates)
        items.append((rank,i,row))
    items.sort(key=lambda x:(x[0],x[1]))
    output=[x[2] for x in items]
    if len(output)!=len(rows) or len({(x['cardyssey_karte'],x['variante_id']) for x in output})!=len(rows):
        raise ValueError('Queue rows lost/duplicated')
    return output,{'tiers':dict(sorted(Counter(x[0] for x in items).items())),
      'first15':[{'cardId':r['cardyssey_karte'],'print':str(r.get('foil') or r.get('stempel') or r.get('drucktyp') or ''),
                  'tier':n} for n,_,r in items[:15]]}

def load_latest(path):
    latest={}
    if not path.is_file():return latest
    with path.open(encoding='utf-8-sig') as f:
        for line in f:
            try:
                a=json.loads(line)
                if a.get('card_id') and a.get('variant_id') and a.get('status'):
                    latest[(a['card_id'],a['variant_id'])]=a
            except (json.JSONDecodeError,KeyError,TypeError):continue
    return latest
def pending_candidates():
    cmd=['docker','exec','cardyssey-db','psql','-X','-qAt','-U','cardyssey','-d','cardyssey',
      '-v','ON_ERROR_STOP=1','-c',
      """SELECT COALESCE(json_agg(DISTINCT jsonb_build_object(
      'language',language_code,'cardId',card_id,'variantId',variant_id)),'[]'::json)::text
      FROM cardmarket_variant_mappings WHERE mapping_status='PENDING_REVIEW'"""]
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
    if proc.returncode:raise RuntimeError(proc.stderr[-350:])
    return {(r['language'],r['cardId'],r['variantId']) for r in json.loads(proc.stdout.strip() or '[]')}
def run(base=BASE,apply=False,candidates=None,recheck_open=False,now=None):
    if recheck_open and not apply:raise ValueError('recheck_open requires apply')
    candidates=pending_candidates() if candidates is None else candidates
    stamp=now or datetime.now(timezone.utc)
    sentinel=base/'open-print-recheck-once-20261111.json'
    mark_rechecks=bool(recheck_open and not sentinel.exists())
    report={'mode':'APPLY' if apply else 'DRY_RUN','selectedOpenMappingCases':len(candidates),
       'recheckOpenRequested':recheck_open,'recheckAlreadyScheduled':bool(recheck_open and sentinel.exists()),
       'languages':{}}
    for lang in ('de','en'):
        path=base/f'queue-{lang}.csv'
        with (base/f'queue-{lang}.review.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            with path.open(encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f);fields=list(reader.fieldnames or []);rows=list(reader)
            latest=load_latest(base/f'browser-observations-{lang}.jsonl')
            specific={(card,var) for language,card,var in candidates if language==lang}
            marked=0
            # New special-print interpretation warrants exactly ONE retry
            # for cases already seen this epoch, without touching successes.
            if mark_rechecks:
                for row in rows:
                    key=(row['cardyssey_karte'],row['variante_id'])
                    previous=latest.get(key)
                    if key not in specific or not previous or previous.get('status') not in FAILED:continue
                    seen=moment(previous.get('seen_at'))
                    requested=moment(row.get('manual_scan_requested_at'))
                    if seen and (not requested or requested<=seen):
                        row['manual_scan_requested_at']=stamp.isoformat()
                        marked+=1
            out,stats=prioritize(rows,latest,specific)
            report['languages'][lang]={'total':len(rows),
               'openMappingCasesInQueue':sum((a['cardyssey_karte'],a['variante_id']) in specific for a in rows),
               'specialRecheckMarked':marked,**stats}
            if apply:
                fd,temp=tempfile.mkstemp(prefix=f'cardmarket-priority-{lang}-',suffix='.csv',dir=base)
                try:
                    with os.fdopen(fd,'w',newline='',encoding='utf-8-sig') as f:
                        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(out)
                    os.replace(temp,path)
                finally:
                    if os.path.exists(temp):os.unlink(temp)
    if apply:
        if mark_rechecks:
            sentinel.write_text(json.dumps({'requestedAt':stamp.isoformat(),
                'markedCases':sum(z['specialRecheckMarked'] for z in report['languages'].values()),
                'purpose':'ONE_TIME_NEW_PRINT_CLASSIFIER_RECHECK'},ensure_ascii=False)+'\n')
        target=base/'recovery-queue-priority-report.json'
        with target.open('w',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--apply',action='store_true')
    p.add_argument('--recheck-open',action='store_true',help='one-time special-print recheck; implies --apply')
    args=p.parse_args()
    result=run(apply=args.apply,recheck_open=args.recheck_open)
    print(json.dumps(result,ensure_ascii=False))
