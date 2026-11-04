#!/usr/bin/env python3
"""Admin-only CLI for durable human classification of a catalog card.
The invoking authenticated Next.js API enforces admin permissions.
"""
import json,sys,re
from price_history import db,sql

STATUSES={'AUTO','NO_VERIFIED_SALE','OFFER_REVIEW','VERIFIED'}
DAYS={7,14,30}

def change(card,status,days,show,note):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{2,90}',card):raise ValueError('invalid_card')
    if status not in STATUSES or days not in DAYS or not isinstance(show,bool):raise ValueError('invalid_review')
    # Admin-facing final states always have fixed, reliable refresh cadences.
    days=30 if status=='NO_VERIFIED_SALE' else 7 if status=='VERIFIED' else days
    if not isinstance(note,str) or len(note)>500:raise ValueError('invalid_note')
    if db('SELECT count(*) FROM catalog_cards_mirror WHERE card_id='+sql(card)+" AND language_code='de';")=='0':raise ValueError('unknown_card')
    db('''INSERT INTO ebay_card_review(card_id,language_code,review_status,refresh_days,show_offer_references,note)
        VALUES('''+sql(card)+",'de',"+sql(status)+','+str(days)+','+('TRUE' if show else 'FALSE')+','+sql(note)+''')
        ON CONFLICT(card_id,language_code) DO UPDATE SET review_status=EXCLUDED.review_status,
        refresh_days=EXCLUDED.refresh_days,show_offer_references=EXCLUDED.show_offer_references,
        note=EXCLUDED.note,updated_at=now();''')
    return {'cardId':card,'status':status,'refreshDays':days,'showOfferReferences':show,'note':note}

if __name__=='__main__':
    try:
        obj=json.loads(sys.stdin.read())
        print(json.dumps(change(obj['cardId'],obj['status'],obj['refreshDays'],obj['showOfferReferences'],obj.get('note',''))))
    except (ValueError,KeyError,TypeError) as err:
        print(json.dumps({'error':str(err)}));sys.exit(2)
