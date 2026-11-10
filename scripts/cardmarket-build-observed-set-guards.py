#!/usr/bin/env python3
"""Derive only independently repeated set/slug evidence from completed
official-catalog direct-ID browser lookups. No ID/print/price publication.
The existing human set guards always override this optional cache.
"""
import argparse,csv,json,re
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path('/home/tv/cardshop')
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
PATTERN=re.compile(r'^/(de|en)/Pokemon/Products/Singles/([A-Za-z0-9-]+)/([A-Za-z0-9-]+)$')
def derive(base=BASE,minimum=5):
    with (base/'queue-de.csv').open(encoding='utf-8-sig',newline='') as f:
        rows={(r['cardyssey_karte'],r['variante_id']):r for r in csv.DictReader(f)}
    latest={}
    with (base/'browser-observations-de.jsonl').open(encoding='utf-8-sig') as f:
        for line in f:
            try:
                item=json.loads(line);latest[(item['card_id'],item['variant_id'])]=item
            except (ValueError,TypeError,KeyError):continue
    evidence=defaultdict(lambda:defaultdict(set))
    for key,item in latest.items():
        row=rows.get(key)
        if not row or item.get('catalog_direct_id_verified') is not True or item.get('card_number_url_verified') is not True:continue
        pid=str(item.get('product_id') or '')
        if not pid.isdigit() or pid!=str(row.get('catalog_singleton_id') or ''):continue
        if not str(row.get('catalog_expansion_id') or '').isdigit():continue
        try:u=urlsplit(item.get('url',''))
        except (ValueError,TypeError):continue
        if u.scheme!='https' or u.hostname!='www.cardmarket.com':continue
        m=PATTERN.fullmatch(u.path)
        if not m:continue
        evidence[row['set_id']][m.group(2)].add(row['cardyssey_karte'])
    approved={};excluded={}
    for sid,group in sorted(evidence.items()):
        if len(group)==1:
            slug,ids=next(iter(group.items()))
            if len(ids)>=minimum:approved[sid]={'setSlug':slug,'distinctLiveCards':len(ids),'proof':'OFFICIAL_PRODUCT_ID_AND_LIVE_NUMBER_AND_UNIQUE_SET_PATH'}
        else:excluded[sid]={s:len(v) for s,v in group.items()}
    return {'generatedAt':datetime.now(timezone.utc).isoformat(),
            'minimumDistinctCards':minimum,'setSlugs':approved,
            'ambiguousExcluded':excluded,'verifiedPrints':0,'publishedPrices':0}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--min-cards',type=int,default=5)
    a=p.parse_args()
    if not 5<=a.min_cards<=100:raise SystemExit('min-cards out of range')
    d=derive(minimum=a.min_cards)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    import os,tempfile
    fd,temp=tempfile.mkstemp(prefix='observed-set-',suffix='.tmp',dir=a.output.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(d,f,indent=2,ensure_ascii=False)
        os.replace(temp,a.output)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    print(json.dumps({'approved':len(d['setSlugs']),'excluded':d['ambiguousExcluded'],
                      'setSlugs':{k:v['setSlug'] for k,v in d['setSlugs'].items()}},ensure_ascii=False))
