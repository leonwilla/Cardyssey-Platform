#!/usr/bin/env python3
"""Safe same-product page leads across DE and EN.

No assumption that a translated name, a shared drawing, or a V1/V2 label is
the exact physical print. A lead is created only when BOTH queues identify
the same Cardyssey card+variant and the exact same official singleton product
ID; the originating live page must independently confirm product ID and
collector number. The destination browser MUST revalidate idProduct, set and
number; cached paths never certify a language-variant price.
"""
from __future__ import annotations
import argparse,csv,json,os,re,tempfile
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
URL_RE=re.compile(r'^/(?:de|en)/Pokemon/Products/Singles/([A-Za-z0-9-]+)/([A-Za-z0-9-]+)$')
def ordinary(r):
    return bool(r.get('drucktyp','').casefold() in {'normal','reverse'}
       and not r.get('foil') and not r.get('sonderdruck')
       and str(r.get('stempel') or '') in ('','[]','null'))
def page_url(url,lang):
    try:u=urlsplit(str(url or ''))
    except (ValueError,TypeError):return None
    if (u.scheme!='https' or u.hostname!='www.cardmarket.com'
        or u.port not in (None,443) or u.username or u.password):return None
    m=URL_RE.fullmatch(u.path)
    if not m:return None
    # Deliberately strip offer filters: DE and EN use different language
    # params; a print-specific filter must be rebuilt and verified in browser.
    return f'https://www.cardmarket.com/{lang}/Pokemon/Products/Singles/{m.group(1)}/{m.group(2)}'

def load_queue(base,language):
    with (base/f'queue-{language}.csv').open(encoding='utf-8-sig',newline='') as f:
        return {(r['cardyssey_karte'],r['variante_id']):r for r in csv.DictReader(f)}
def last_observations(base,language):
    latest={}
    path=base/f'browser-observations-{language}.jsonl'
    if not path.exists():return latest
    with path.open(encoding='utf-8-sig') as f:
        for line in f:
            try:
                x=json.loads(line)
                key=(x['card_id'],x['variant_id'])
                latest[key]=x
            except (ValueError,KeyError,TypeError):pass
    return latest

def build(base=BASE):
    q={l:load_queue(base,l) for l in ('de','en')}
    latest={l:last_observations(base,l) for l in ('de','en')}
    entries={};conflicts=set();counts=Counter()
    for src,dst in (('de','en'),('en','de')):
        for key,x in latest[src].items():
            source=q[src].get(key);target=q[dst].get(key)
            if not source or not target or not ordinary(source) or not ordinary(target):continue
            if source.get('set_id')!=target.get('set_id'):continue
            counts['sameCardOrdinary']+=1
            if not (x.get('catalog_direct_id_verified') is True and
                    x.get('card_number_url_verified') is True and
                    x.get('identity_confirmed') is True):continue
            pid=str(x.get('product_id') or '')
            if not re.fullmatch(r'[0-9]{4,12}',pid):continue
            if pid!=source.get('catalog_singleton_id') or pid!=target.get('catalog_singleton_id'):continue
            if str(source.get('catalog_expansion_id'))!=str(target.get('catalog_expansion_id')):continue
            url=page_url(x.get('url'),dst)
            if not url:continue
            slug=urlsplit(url).path.split('/')[5]
            # A verified source page is still only a lead in the target language.
            k='|'.join((dst,key[0],key[1]))
            record={'sourceLanguage':src,'destinationLanguage':dst,
                    'cardId':key[0],'variantId':key[1],'productId':pid,
                    'setId':str(source['set_id']),'officialExpansionId':str(source['catalog_expansion_id']),
                    'url':url,'catalogProductIdValidatedAtSource':True,
                    'targetProductValidated':False,'exactPrintVerified':False,
                    'languagePriceVerified':False}
            if k in entries and entries[k]['productId']!=pid:
                conflicts.add(k);continue
            entries[k]=record
            counts['candidate']+=1
    for key in conflicts:entries.pop(key,None)
    return {'schema':1,'source':'OFFICIAL_SINGLETON_AND_LIVE_NUMBER_CONFIRMED_CANDIDATE_ONLY',
            'validatedPrints':0,'publishedPrices':0,'stats':dict(counts),
            'conflictsDropped':len(conflicts),'entries':entries}
def write(data,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(dir=path.parent,prefix='cm-crosslang-',suffix='.json.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,separators=(',',':'))
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();data=build();write(data,a.output)
    print(json.dumps({'entries':len(data['entries']),
        'conflictsDropped':data['conflictsDropped'],'stats':data['stats'],
        'publishedPrices':False,'printVerified':False},ensure_ascii=False))
