#!/usr/bin/env python3
"""Audit fast Cardmarket guide coverage without publishing unverified prices.

Guide is European product/finish aggregate, NOT language-, edition-, condition-
or stamp-specific. Candidate IDs are never silently promoted to verified IDs.
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
import hashlib
import json
from collections import Counter
from pathlib import Path

PRICE_URL='https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json'
DEFAULT_CACHE=Path('/home/tv/.local/state/cardyssey-queue/price-feeds')/(hashlib.sha256(PRICE_URL.encode()).hexdigest()+'.json')


def classify(row, guide):
    ids=sorted({x.strip() for x in str(row.get('cardmarket_ids') or '').split(',') if x.strip().isdigit()})
    special=bool(str(row.get('sonderdruck') or '').strip() or str(row.get('foil') or '').strip() or str(row.get('stempel') or '').strip() not in ('','[]','null'))
    finish=str(row.get('drucktyp') or '').strip().casefold()
    bucket='avg30-holo' if finish=='reverse' else 'avg30' if finish in ('normal','holo') else None
    if not ids:return 'NO_PRODUCT_ID',None
    if len(ids)>1:return 'MULTIPLE_PRODUCT_IDS',None
    pid=ids[0]
    if row.get('routing_state')!='VERIFIED_PRODUCT_ID':return 'SINGLE_ID_NEEDS_IDENTITY_VERIFICATION',None
    if special:return 'SPECIAL_PRINT_NEEDS_REVIEW',None
    if bucket is None:return 'UNSUPPORTED_FINISH',None
    entry=guide.get(pid)
    if entry is None:return 'NOT_IN_GUIDE',None
    value=entry.get(bucket)
    if not isinstance(value,(float,int)) or isinstance(value,bool) or value<=0:return 'NO_GUIDE_PRICE',None
    return 'VERIFIED_PRODUCT_GUIDE_PREVIEW',{'product_id':pid,'guide_bucket':bucket,'aggregate_eur':value}


def audit(rows,guide):
    stats=Counter();preview=[]
    for row in rows:
        classification,quote=classify(row,guide)
        stats[classification]+=1
        if quote:
            preview.append({'card_id':row['cardyssey_karte'],'variant_id':row['variante_id'],**quote})
    return dict(stats),preview


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--queue',type=Path,required=True)
    ap.add_argument('--cached-guide',type=Path,default=DEFAULT_CACHE)
    ap.add_argument('--report',type=Path,required=True)
    args=ap.parse_args()
    with args.queue.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    payload=json.loads(args.cached_guide.read_text())
    prices={str(x['idProduct']):x for x in payload.get('priceGuides',[])}
    if len(prices)<50000:raise ValueError('Incomplete price guide')
    stats,preview=audit(rows,prices)
    report={'source':'CARDMARKET_OFFICIAL_PRICE_GUIDE','guide_date':payload.get('createdAt'),
        'price_guide_products':len(prices),'variants':len(rows),'counts':stats,
        'preview_count':len(preview),'language_specific':False,'condition_specific':False,
        'edition_specific':False,'print_identity_certified':False,'published':False,
        'notes':'Guide-only reference candidates; no language-specific NM price and no overwrite of tcg_price_cache.',
        'verified_id_previews':preview}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='verified_id_previews'},ensure_ascii=False))

if __name__=='__main__':main()
