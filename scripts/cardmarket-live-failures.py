#!/usr/bin/env python3
"""Paginated admin-only scan failures, read directly from scanner JSONL logs.
The worklist remains distinct from catalog print review. No guesses or writes.
"""
import argparse,csv,json,importlib.util
from datetime import datetime,timezone
from pathlib import Path
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
spec=importlib.util.spec_from_file_location('filter_readiness',Path(__file__).with_name('cardmarket-filter-readiness.py'))
filter_readiness=importlib.util.module_from_spec(spec);spec.loader.exec_module(filter_readiness)
SUCCESS={'MAPPED_NO_PRICE_REQUIRED','COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED','COMPLETE_FILTERED_ASKING_MEDIAN','SOURCE_ONLY','SUCCESS','SET_MAPPING_PENDING'}
PRICE_LIMIT_STATUSES={'FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE','NO_CONFIRMED_FILTERED_OFFERS','FILTER_UNAVAILABLE','FILTER_UNVERIFIED_EMPTY','FILTER_NOT_APPLIED'}
TECHNICAL={'BLOCKED','LOGIN_REQUIRED','ERROR','PROVIDER_ERROR','PROVIDER_TIMEOUT','CONNECTION_LOST','FILTER_UNAVAILABLE','FILTER_UNVERIFIED_EMPTY','FILTER_NOT_APPLIED','NO_CONFIRMED_FILTERED_OFFERS','FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE'}

def classify(status,entry=None,queue=None):
    # Card+product match is established. Incomplete price pagination does NOT
    # create an identity/print decision for the founder. Scope this rule to
    # 30th sets until other releases have been independently audited.
    if status in PRICE_LIMIT_STATUSES and entry and queue and str(queue.get('set_id') or '').startswith('30th'):
        pid=str(entry.get('product_id') or '')
        candidates={x.strip() for x in str(queue.get('cardmarket_ids') or '').split(',') if x.strip()}
        known_route=str(queue.get('known_url') or '')
        if entry.get('identity_confirmed') is True and pid.isdigit() and pid in candidates and (known_route or queue.get('routing_state')=='VERIFIED_PRODUCT_ID'):
            return 'PREISPRUEFUNG'
        if entry.get('identity_confirmed') is True and pid.isdigit() and candidates and pid not in candidates:
            return 'ZUORDNUNG'

    if status=='MISSING_REQUIRED_SCAN_FIELDS':return 'DATEN_FEHLEN'
    if status in SUCCESS:return None
    if status in TECHNICAL or status.startswith('DEFERRED') or status.startswith('FILTER_') or status.startswith('NO_CONFIRMED'):return 'TECHNISCH'
    if status.startswith('COMPLETE_') or status in ('STARTED','RUNNING'):return None
    return 'ZUORDNUNG'

def list_failures(base=BASE,language='de',page=0,search='',scope='current',kind='karten'):
    if language not in ('de','en'):raise ValueError('invalid_language')
    if scope not in ('current','all'):raise ValueError('invalid_scope')
    if kind not in ('karten','preise','technik','alle'):raise ValueError('invalid_kind')
    if not 0<=page<=2000:raise ValueError('invalid_page')
    epoch=None
    ep=base/'full-rescan-epoch.json'
    if ep.exists():
        try:epoch=datetime.fromisoformat(json.loads(ep.read_text(encoding='utf-8-sig'))['requestedAt'].replace('Z','+00:00'))
        except (ValueError,KeyError):pass
    rows={}
    p=base/f'browser-observations-{language}.jsonl'
    if p.exists():
        with p.open(encoding='utf-8-sig') as f:
            for line in f:
                try:entry=json.loads(line)
                except (TypeError,ValueError):continue
                card=str(entry.get('card_id') or '');var=str(entry.get('variant_id') or '')
                if not card or not var:continue
                if scope=='current' and epoch:
                    try:
                        seen=datetime.fromisoformat(str(entry.get('seen_at','')).replace('Z','+00:00'))
                        if seen<epoch:continue
                    except ValueError:continue
                rows[(card,var)]=entry
    queue={}
    with (base/f'queue-{language}.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):queue[(r.get('cardyssey_karte'),r.get('variante_id'))]=r
    output=[]
    for key,entry in rows.items():
        status=str(entry.get('status') or '')
        q=queue.get(key,{})
        group=classify(status,entry,q)
        if not group:continue
        card,var=key
        readiness=filter_readiness.analyze(q) if q else {'missing':[],'unsupported':[]}
        item={'missingFields':entry.get('missing_fields') or readiness['missing'],
          'unfilterablePrintFeatures':readiness['unsupported'],
          'cardId':card,'variantId':var,'setId':q.get('set_id') or entry.get('set_id') or card.rsplit('-',1)[0],
          'name':q.get('kartenname_suche') or entry.get('name') or card,
          'language':language,'status':status,'type':group,
          'detail':str(entry.get('error') or entry.get('pagination_failure') or entry.get('reason') or '')[:220],
          'productId':str(entry.get('product_id') or ''), 'seenAt':entry.get('seen_at') or ''}
        if search.strip() and search.strip().casefold() not in ' '.join(str(v) for v in item.values()).casefold():continue
        output.append(item)
    output.sort(key=lambda e:e['seenAt'],reverse=True)
    full_counts={'assignment':sum(x['type']=='ZUORDNUNG' for x in output),
            'technical':sum(x['type']=='TECHNISCH' for x in output),
            'priceChecks':sum(x['type']=='PREISPRUEFUNG' for x in output),
            'missingData':sum(x['type']=='DATEN_FEHLEN' for x in output)}
    if kind=='karten':output=[x for x in output if x['type'] in ('ZUORDNUNG','DATEN_FEHLEN')]
    elif kind=='preise':output=[x for x in output if x['type']=='PREISPRUEFUNG']
    elif kind=='technik':output=[x for x in output if x['type']=='TECHNISCH']
    return {'language':language,'scope':scope,'kind':kind,'total':len(output),'page':page,'pageSize':50,
            **full_counts,
            'items':output[page*50:(page+1)*50]}
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--language',choices=['de','en'],default='de');a.add_argument('--scope',choices=['all','current'],default='current');a.add_argument('--page',type=int,default=0);a.add_argument('--search',default='');a.add_argument('--kind',choices=['karten','preise','technik','alle'],default='karten');v=a.parse_args()
    print(json.dumps(list_failures(language=v.language,page=v.page,search=v.search,scope=v.scope,kind=v.kind),ensure_ascii=False))
