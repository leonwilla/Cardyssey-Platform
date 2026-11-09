#!/usr/bin/env python3
"""Read-only, bounded DE/EN Cardmarket collector status for authenticated admin UI."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
PROBLEMS={'ERROR','NO_EXACT_NUMBER_SEARCH_HIT','PRODUCT_SET_SLUG_MISMATCH','MULTIPLE_SEARCH_HITS','NO_PRODUCT_ID','PRODUCT_ID_NOT_IN_VERIFIED_SET','FILTER_UNAVAILABLE','FILTER_NOT_APPLIED','FILTER_UNVERIFIED_EMPTY','DEFERRED_SOCKET','DEFERRED_PROVIDER_TIMEOUT','NO_CONFIRMED_FILTERED_OFFERS'}

def snapshot(base:Path,language:str):
    if language not in ('de','en'):raise ValueError('unsupported language')
    queue=base/f'queue-{language}.csv'
    with queue.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    expected={(r['cardyssey_karte'],r['variante_id']) for r in rows}
    browser={(r['cardyssey_karte'],r['variante_id']) for r in rows}
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
    total=len(expected);done=len(scanned)
    matched=sum(bool(r.get('identity_confirmed')) for r in completed.values())
    search_misses=sum(r.get('status')=='NO_EXACT_NUMBER_SEARCH_HIT' for r in completed.values())
    priced=sum(r.get('needs_price')=='NO' and r.get('existing_price_eur') not in ('',None) for r in rows)
    missing=sum(r.get('needs_price')=='YES' for r in rows)
    eligible_missing=sum(r.get('needs_price')=='YES' and str(r.get('scan_tier'))!='4' for r in rows)
    bulk_missing=sum(r.get('needs_price')=='YES' and str(r.get('scan_tier'))=='4' for r in rows)
    return {'language':language,'totalVariants':total,'uniqueCards':len({r['cardyssey_karte'] for r in rows}),
       'browserTotal':len(browser),'feedOnly':sum(str(r.get('scan_tier'))=='4' and r.get('needs_price')=='NO' for r in rows),'browserObserved':len(completed),
       'browserProcessed':done,'productMapped':matched,'noExactSearchMatch':search_misses,
       'pricedVariants':priced,'missingVariants':missing,'browserMissingPriority':eligible_missing,'feedMissingPriority':bulk_missing,
       'browserRemaining':max(0,len(browser)-done),
       'progressPercent':round(done/len(browser)*100,2) if browser else 100,
       'totalReviewedPercent':round((total-len(browser)+done)/total*100,2) if total else 100,
       'status':str(progress.get('status') or 'NOT_STARTED'),
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
