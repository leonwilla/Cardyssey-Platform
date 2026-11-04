"""Separate candidate references; selection-listing sales do not certify a specific print."""
import json,re
from price_history import db,sql

MULTI=re.compile(r'\b(?:auswahl|aussuchen|auswählen|choose|select\s+your|pick\s+your|einzelkarten|karten\s+zum\s+auswählen)\b',re.I)


def store_offer_candidates(report,card):
    candidates=[]
    for row in report.get('rows',[]):
        title=row.get('title','')
        if not MULTI.search(title):continue
        if not re.search(r'karmesin|purpur|pokemon|pokémon|svp|sv01|sv02|paldea|30 jahre',title,re.I):continue
        if not re.fullmatch(r'\d{9,15}',str(row.get('item_id',''))):continue
        candidates.append(dict(item_id=row['item_id'],title=title[:500],url=row.get('url') or '',
                               image_url=row.get('image_url'),price=row.get('price_eur')))
        if len(candidates)>=8:break
    if not candidates:return 0
    query=("INSERT INTO ebay_offer_reference(card_id,language_code,ebay_item_id,title,listing_url,image_url,displayed_price_eur,reference_kind) "
      "SELECT "+sql(card['card_id'])+",'de',r.item_id,r.title,r.url,r.image_url,r.price,'MULTI_SELECT_UNVERIFIED_CARD' "
      "FROM jsonb_to_recordset("+sql(json.dumps(candidates,ensure_ascii=False))+"::jsonb) "
      "AS r(item_id text,title text,url text,image_url text,price numeric) "
      "ON CONFLICT(card_id,language_code,ebay_item_id) DO UPDATE SET "
      "title=EXCLUDED.title,last_seen_at=now(),image_url=EXCLUDED.image_url,"
      "displayed_price_eur=EXCLUDED.displayed_price_eur;")
    db(query)
    return len(candidates)
