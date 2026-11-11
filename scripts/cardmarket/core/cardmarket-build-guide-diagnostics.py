#!/usr/bin/env python3
"""Compact read-only, PRODUCT-WIDE Cardmarket guide context for the browser.

A product-level trend/avg30 has no DE/EN/NM/foil guarantee. This file is
diagnostic evidence only: never publish into tcg_price_cache or routing.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
from cardmarket_game_profile import load_game_profile
import argparse,csv,hashlib,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('/home/tv/cardshop')
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
URL=load_game_profile()['price_url']
CACHE=Path('/home/tv/.local/state/cardyssey-queue/price-feeds')
def build(base=BASE,cache=CACHE):
    source=cache/(hashlib.sha256(URL.encode()).hexdigest()+'.json')
    feed=json.loads(source.read_text(encoding='utf-8'))
    if len(feed.get('priceGuides') or [])<50000:raise ValueError('Price guide incomplete')
    needed=set()
    for lang in ('de','en'):
        with (base/f'queue-{lang}.csv').open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                for pid in (str(row.get('cardmarket_ids') or '')+','+
                            str(row.get('catalog_singleton_id') or '')).split(','):
                    if pid.isdigit():needed.add(pid)
    prices={}
    for item in feed['priceGuides']:
        pid=str(item.get('idProduct') or '')
        if pid not in needed:continue
        prices[pid]={k:item.get(k) for k in ('trend','trend-holo','avg30','avg30-holo')
                     if isinstance(item.get(k),(int,float)) and item.get(k)>0}
    return {'createdAt':feed.get('createdAt'),'extractedAt':datetime.now(timezone.utc).isoformat(),
            'scope':'PRODUCT_AGGREGATE_NOT_LANGUAGE_CONDITION_OR_EXACT_PRINT',
            'canPublishAsLanguagePrintPrice':False,'products':prices}
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);args=a.parse_args()
    d=build();args.output.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='price-guide-diagnostic-',suffix='.tmp',dir=args.output.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,separators=(',',':'))
        os.replace(temp,args.output)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    print(json.dumps({'guideDate':d['createdAt'],'products':len(d['products']),
                       'canPublishAsLanguagePrintPrice':False}))
