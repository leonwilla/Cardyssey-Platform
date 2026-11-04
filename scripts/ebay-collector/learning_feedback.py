#!/usr/bin/env python3
"""Structured verified admin examples. Does NOT alter imports, prices or rules.

Each example can be converted into a regression fixture after human review;
this is safer than treating individual corrections as a self-training model.
"""
import json,re,sys
from price_history import db,sql

DECISIONS={'WRONG_CARD','VALID_SINGLE_SALE','MULTI_SELECTION','WRONG_VARIANT','PAID_PRICE_UNKNOWN','OTHER'}

def record(card_id,item_id,decision,note,title):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{2,90}',card_id) or not re.fullmatch(r'\d{9,15}',item_id):raise ValueError('invalid_identity')
    if decision not in DECISIONS:raise ValueError('invalid_decision')
    if not isinstance(note,str) or len(note)>1000 or not isinstance(title,str) or len(title)>500:raise ValueError('invalid_text')
    if db('SELECT count(*) FROM catalog_cards_mirror WHERE card_id='+sql(card_id)+" AND language_code='de';")=='0':raise ValueError('unknown_card')
    db('''INSERT INTO ebay_listing_feedback(card_id,ebay_item_id,language_code,decision,note,listing_title)
      VALUES ('''+sql(card_id)+','+sql(item_id)+",'de',"+sql(decision)+','+sql(note)+','+sql(title)+''')
      ON CONFLICT(card_id,ebay_item_id,language_code) DO UPDATE SET
        decision=EXCLUDED.decision,note=EXCLUDED.note,
        listing_title=EXCLUDED.listing_title,last_reviewed_at=now();''')
    return dict(cardId=card_id,itemId=item_id,decision=decision,saved=True,affectsPrice=False)

if __name__=='__main__':
    try:
        o=json.loads(sys.stdin.read())
        print(json.dumps(record(o['cardId'],o['itemId'],o['decision'],o.get('note',''),o.get('title',''))))
    except (ValueError,TypeError,KeyError) as exc:
        print(json.dumps({'error':str(exc)}));raise SystemExit(2)
