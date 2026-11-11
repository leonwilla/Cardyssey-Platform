#!/usr/bin/env python3
"""Official catalog metacard-family *candidate* index for the full DE/EN queue.

idMetacard groups printings including separate Additional expansions, but
does not certify Cardyssey identity, collector number, foil or price. Index
keeps original official expansion IDs to avoid cross-set autopromotion.
"""
import argparse,csv,hashlib,json,os,re,tempfile
from collections import defaultdict,Counter
from pathlib import Path
ROOT=Path('/home/tv/cardshop')
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
URL='https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json'
FEEDS=Path('/home/tv/.local/state/cardyssey-queue/price-feeds')
def build(base=BASE,feeds=FEEDS):
    p=feeds/(hashlib.sha256(URL.encode()).hexdigest()+'.json')
    products=json.loads(p.read_text(encoding='utf-8'))['products']
    by_id={str(x['idProduct']):x for x in products if x.get('idProduct')}
    by_meta=defaultdict(list)
    for x in products:
        if x.get('idMetacard'):by_meta[str(x['idMetacard'])].append(x)
    result={};summary=Counter()
    for lang in ('de','en'):
        cards=defaultdict(lambda:{'setId':None,'seeds':set(),'variants':0})
        with (base/f'queue-{lang}.csv').open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                card=r['cardyssey_karte'];d=cards[card];d['setId']=r['set_id'];d['variants']+=1
                if r.get('candidate_status')=='SET_EXPANSION_AMBIGUOUS':continue
                for val in (str(r.get('cardmarket_ids') or '')+','+
                            str(r.get('set_card_candidate_ids') or '')+','+
                            str(r.get('catalog_singleton_id') or '')).split(','):
                    if re.fullmatch('[0-9]{4,12}',val) and val in by_id:d['seeds'].add(val)
        for card,d in cards.items():
            possible=defaultdict(set)
            for pid in d['seeds']:
                meta=str(by_id[pid].get('idMetacard') or '')
                if meta and meta!='0':possible[meta].add(pid)
            if not possible:continue
            # Distinct families for a single card are ambiguous and cannot
            # safely be merged: retain them as separate, unverified options.
            meta_groups=[]
            for meta,seeds in sorted(possible.items()):
                members=by_meta.get(meta,[])
                if len(members)<2:continue
                meta_groups.append({'metacardId':meta,'seedProductIds':sorted(seeds),
                  'candidateProducts':[{'id':str(x['idProduct']),
                     'expansionId':str(x.get('idExpansion') or ''),
                     'name':str(x.get('name') or '')[:170]}
                    for x in members[:30]],'truncated':len(members)>30,
                  'multipleExpansions':len({str(x.get('idExpansion')) for x in members})>1,
                  'printIdentityVerified':False})
            if meta_groups:
                result[lang+'|'+card]={'cardId':card,'language':lang,'setId':d['setId'],
                    'seedIsVerifiedPrint':False,'families':meta_groups}
                summary[lang+'_cards']+=1
                if len(meta_groups)>1:summary[lang+'_multipleFamilies']+=1
                if any(x['multipleExpansions'] for x in meta_groups):summary[lang+'_crossExpansionFamilies']+=1
    return {'source':'CARDMARKET_OFFICIAL_PRODUCT_CATALOG_METACARD_ONLY',
            'printIdentityVerified':False,'pricesPublished':0,
            'summary':dict(summary),'cards':result}
def write(data,path:Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='cm-family-',suffix='.json.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,separators=(',',':'))
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();x=build();write(x,a.output)
    print(json.dumps({'summary':x['summary'],'indexedCards':len(x['cards']),
       'printVerified':False,'pricesPublished':0},ensure_ascii=False))
