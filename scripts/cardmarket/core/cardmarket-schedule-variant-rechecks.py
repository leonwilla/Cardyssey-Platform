#!/usr/bin/env python3
"""Schedule bounded, non-destructive rechecks of failed/multiple-print Cardmarket cards.

Only changes CSV manual_scan_requested_at; keeps old observations, DB prices,
all product IDs and review decisions. Existing Windows scheduled runner picks
these up before routine scans. A separate JSON manifest records selection.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse
import csv
import fcntl
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
ROOT=Path('/home/tv/cardshop')
FAILS={
 'MULTIPLE_SEARCH_HITS','PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED',
 'PRODUCT_ID_NOT_VERIFIED_FOR_CARD','PRODUCT_ID_NOT_IN_VERIFIED_SET',
 'NO_PRODUCT_ID','FILTER_UNAVAILABLE','FILTER_NOT_APPLIED',
 'FILTER_UNVERIFIED_EMPTY','NO_CONFIRMED_FILTERED_OFFERS',
 'PRODUCT_SET_SLUG_MISMATCH','SET_MAPPING_PENDING','NO_EXACT_NUMBER_SEARCH_HIT'
}
FOCUS={'sv01-013','sv10.5w-033','base1-8','basep-1','basep-4'}
def special(r):
    return bool((r.get('foil') or '').strip() or (r.get('sonderdruck') or '').strip()
                or (r.get('stempel') or '').strip() not in ('','[]','null')
                or (r.get('drucktyp') or '').lower() not in ('normal','reverse'))
def select(language, *, limit, base=BASE, now=None, dry_run=False):
    if language not in ('de','en') or not 1<=limit<=400:
        raise ValueError('Invalid language or safe recheck limit')
    path=base/f'queue-{language}.csv'
    observations=base/f'browser-observations-{language}.jsonl'
    latest={}
    with observations.open(encoding='utf-8-sig') as f:
        for line in f:
            try: rec=json.loads(line);latest[(rec['card_id'],rec['variant_id'])]=rec
            except (ValueError,KeyError,TypeError):continue
    stamp=(now or datetime.now(timezone.utc)).isoformat()
    with (base/f'queue-{language}.review.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f); fields=list(reader.fieldnames or []);rows=list(reader)
        if 'manual_scan_requested_at' not in fields:
            fields.append('manual_scan_requested_at')
        options=[]
        for row in rows:
            key=row['cardyssey_karte'],row['variante_id']
            prior=latest.get(key)
            if not prior or prior.get('status') not in FAILS:continue
            failed=prior['status']
            # The historical 8k zero-hit searches are usually old missing
            # search-result DOM data. Do not starve useful new cards with all.
            if failed=='NO_EXACT_NUMBER_SEARCH_HIT' and not (special(row) or key[0] in FOCUS):
                continue
            is_special=special(row)
            print_versions=len([v for v in row.get('cardmarket_ids','').split(',') if v.isdigit()])
            if not is_special and failed=='NO_EXACT_NUMBER_SEARCH_HIT' and key[0] not in FOCUS:
                continue
            # Round-robin among cards, not thousands of the same promo variants.
            tier=(
              0 if key[0] in FOCUS else
              1 if is_special and failed in ('MULTIPLE_SEARCH_HITS','PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED') else
              2 if print_versions>1 and failed in FAILS else
              3 if is_special else
              4
            )
            options.append((tier,0 if is_special else 1, row,prior))
        options.sort(key=lambda z:(z[0],z[1],z[2]['cardyssey_karte'],z[2]['variante_id']))
        # Reserve room for many different cards/sets. A few per card is
        # enough to tell if same-set variant discovery generalizes.
        chosen=[];per_card=Counter()
        for a in options:
            key=a[2]['cardyssey_karte']
            max_variants=6 if key in FOCUS else 2
            if per_card[key]>=max_variants:continue
            chosen.append(a);per_card[key]+=1
            if len(chosen)>=limit:break
        marked={(a[2]['cardyssey_karte'],a[2]['variante_id']) for a in chosen}
        if not dry_run and marked:
            for row in rows:
                if (row['cardyssey_karte'],row['variante_id']) in marked:
                    row['manual_scan_requested_at']=stamp
            fd,tmp=tempfile.mkstemp(prefix=f'variant-retry-{language}-',suffix='.tmp',dir=base)
            try:
                with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
                os.replace(tmp,path)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
    result={'language':language,'requestedAt':stamp,'scheduled':len(chosen),
            'failuresAvailable':len(options),'mode':'DRY_RUN' if dry_run else 'QUEUED',
            'statusCounts':dict(Counter(a[3]['status'] for a in chosen)),
            'focusCards':dict(Counter(a[2]['cardyssey_karte'] for a in chosen if a[2]['cardyssey_karte'] in FOCUS)),
            'cases':[{'cardId':a[2]['cardyssey_karte'],'variantId':a[2]['variante_id'],
                      'name':a[2]['kartenname_suche'],'statusBefore':a[3]['status'],
                      'foil':a[2]['foil'],'stamp':a[2]['stempel'],
                      'cardmarketIds':a[2]['cardmarket_ids'],
                      'lastObservedAt':a[3].get('seen_at')} for a in chosen]}
    if not dry_run:
        reports=ROOT/'reports/cardmarket-review'
        reports.mkdir(parents=True,exist_ok=True)
        (reports/f'variant-retry-{language}-latest.json').write_text(
            json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--language',choices=['de','en'],required=True)
    p.add_argument('--limit',type=int,default=50)
    p.add_argument('--dry-run',action='store_true')
    args=p.parse_args()
    result=select(args.language,limit=args.limit,dry_run=args.dry_run)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))

if __name__=='__main__':
    main()
