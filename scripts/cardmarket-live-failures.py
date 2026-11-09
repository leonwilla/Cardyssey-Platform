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
TECHNICAL={'BLOCKED','LOGIN_REQUIRED','ERROR','PROVIDER_ERROR','PROVIDER_TIMEOUT','CONNECTION_LOST','FILTER_UNAVAILABLE','FILTER_UNVERIFIED_EMPTY','FILTER_NOT_APPLIED','NO_CONFIRMED_FILTERED_OFFERS','FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE'}

def classify(status):
    if status=='MISSING_REQUIRED_SCAN_FIELDS':return 'DATEN_FEHLEN'
    if status in SUCCESS:return None
    if status in TECHNICAL or status.startswith('DEFERRED') or status.startswith('FILTER_') or status.startswith('NO_CONFIRMED'):return 'TECHNISCH'
    if status.startswith('COMPLETE_') or status in ('STARTED','RUNNING'):return None
    return 'ZUORDNUNG'

def list_failures(base=BASE,language='de',page=0,search='',scope='current'):
    if language not in ('de','en'):raise ValueError('invalid_language')
    if scope not in ('current','all'):raise ValueError('invalid_scope')
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
        group=classify(status)
        if not group:continue
        q=queue.get(key,{})
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
    return {'language':language,'scope':scope,'total':len(output),'page':page,'pageSize':50,
            'technical':sum(x['type']=='TECHNISCH' for x in output),
            'assignment':sum(x['type']=='ZUORDNUNG' for x in output),
            'missingData':sum(x['type']=='DATEN_FEHLEN' for x in output),
            'items':output[page*50:(page+1)*50]}
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--language',choices=['de','en'],default='de');a.add_argument('--scope',choices=['all','current'],default='current');a.add_argument('--page',type=int,default=0);a.add_argument('--search',default='');v=a.parse_args()
    print(json.dumps(list_failures(language=v.language,page=v.page,search=v.search,scope=v.scope),ensure_ascii=False))
