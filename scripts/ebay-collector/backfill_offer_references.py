#!/usr/bin/env python3
"""Idempotent, local only: extract unverified selection-offer candidates from saved search reports."""
import json
from pathlib import Path
from offer_references import MULTI
from price_history import db,sql

ROOT=Path('/home/tv/cardyssey-ebay-collector/admin-set-runs')
SETS={'sv01','sv02','30th','30th-c','mep'}

def collect(root=ROOT):
    candidates={}
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.name not in SETS and not any(folder.name.startswith(x+'-history-') for x in SETS):continue
        for p in folder.glob('*/sales.json'):
            card_id=p.parent.name
            if not card_id.startswith(tuple(SETS)):continue
            try:report=json.loads(p.read_text())
            except (OSError,ValueError):continue
            for row in report.get('rows',[]):
                if not MULTI.search(row.get('title','')):continue
                item=str(row.get('item_id',''))
                if not item.isdigit() or not (9<=len(item)<=15):continue
                key=(card_id,item)
                candidates[key]=dict(card_id=card_id,item_id=item,title=row.get('title','')[:500],
                  url=row.get('url') or '',image_url=row.get('image_url'),price=row.get('price_eur'))
    return list(candidates.values())

if __name__=='__main__':
    found=collect()
    if found:
        # One DB call, preserve manual annotations or more recently observed images.
        query=("INSERT INTO ebay_offer_reference(card_id,language_code,ebay_item_id,title,listing_url,image_url,displayed_price_eur,reference_kind) "
          "SELECT r.card_id,'de',r.item_id,r.title,r.url,r.image_url,r.price,'MULTI_SELECT_UNVERIFIED_CARD' "
          "FROM jsonb_to_recordset("+sql(json.dumps(found,ensure_ascii=False))+"::jsonb) "
          "AS r(card_id text,item_id text,title text,url text,image_url text,price numeric) "
          "ON CONFLICT(card_id,language_code,ebay_item_id) DO NOTHING;")
        db(query)
    print(json.dumps({'unverified_offer_candidates':len(found)}))
