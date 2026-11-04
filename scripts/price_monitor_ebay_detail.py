#!/usr/bin/env python3
"""Full saved eBay search evidence, scoped to one card for admin review.
No new eBay requests. Buyer data is never returned.
"""
import json,re,subprocess,sys
from pathlib import Path

sys.path.insert(0,'/home/tv/cardyssey-ebay-collector')
sys.path.insert(0,'/home/tv/cardshop/scripts/ebay-collector')
from anniversary_batch import exact_number,select_rows
from offer_references import MULTI

ROOT=Path('/home/tv/cardyssey-ebay-collector/admin-set-runs')
KINDS=('CONFIRMED_SINGLE','MULTI_SELECTION','OTHER_CARD','COLLECTOR_EXCLUDED','IDENTITY_UNCLEAR')

def evidence(card_id):
    if not re.fullmatch(r'[a-z0-9_-]{2,80}',card_id):raise ValueError('invalid_card')
    base=card_id.split('-')[0]
    found=[]
    for folder in ROOT.iterdir():
        if not folder.is_dir() or not (folder.name==base or folder.name.startswith(base+'-history-') or folder.name.startswith(base+'-pre-')):continue
        manifest=folder/'manifest.json'
        file=folder/card_id/'sales.json'
        if not (manifest.is_file() and file.is_file()):continue
        try:
            card=next((c for c in json.loads(manifest.read_text()) if c.get('card_id')==card_id),None)
            if card:found.append((file.stat().st_mtime,file,card,json.loads(file.read_text())))
        except (OSError,ValueError):pass
    if not found:raise FileNotFoundError('no_report')
    _,file,card,report=max(found,key=lambda x:x[0])
    accepted,_=select_rows(report,card)
    matched={str(r.get('item_id')) for r in accepted if r.get('source')!='EBAY_PURCHASE_HISTORY'}
    results=[]
    for row in report.get('rows',[]):
        if row.get('source')=='EBAY_PURCHASE_HISTORY':continue
        title=str(row.get('title') or '')
        name_ok=all(re.search(r'(?<!\w)'+re.escape(t)+r'(?!\w)',title,re.I) for t in card['name'].split())
        number_ok=exact_number(title,card)
        if str(row.get('item_id')) in matched:kind='CONFIRMED_SINGLE'
        elif MULTI.search(title):kind='MULTI_SELECTION'
        elif not name_ok or (re.search(r'(?<![\w/])\d{1,3}\s*/\s*\d{2,3}(?!\w)',title) and not number_ok):kind='OTHER_CARD'
        elif not row.get('eligible') or row.get('language')!='de':kind='COLLECTOR_EXCLUDED'
        else:kind='IDENTITY_UNCLEAR'
        results.append({'itemId':str(row.get('item_id','')),'title':title[:300],
          'soldDate':row.get('sold_date'),'displayedPrice':row.get('price_eur'),
          'url':row.get('url'),'imageUrl':row.get('image_url'),
          'kind':kind,'collectorExclusions':row.get('exclusions') or '',
          'imageVerified':row.get('image_identity_verified') is True})
    # Unambiguously unrelated cards are useful for collector diagnostics only,
    # not for the human review queue. Keep the count, exclude the rows.
    counts={k:sum(row['kind']==k for row in results) for k in KINDS}
    relevant=[row for row in results if row['kind']!='OTHER_CARD']
    feedback_sql="SELECT ebay_item_id,decision,note FROM ebay_listing_feedback WHERE card_id='"+card_id+"' AND language_code='de';"
    feedback_out=subprocess.run(['docker','exec','cardyssey-db','psql','-X','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',feedback_sql],capture_output=True,text=True,check=True,timeout=12)
    feedback={}
    for line in feedback_out.stdout.splitlines():
        parts=line.split('|',2)
        if len(parts)==3:feedback[parts[0]]={'decision':parts[1],'note':parts[2]}
    for item in relevant:item['feedback']=feedback.get(item['itemId'])
    sql="""SELECT COALESCE(jsonb_agg(jsonb_build_object(
       'itemId',r.ebay_item_id,'title',r.title,'url',r.listing_url,
       'displayedPrice',r.displayed_price_eur,'purchaseStatus',p.status,
       'transactions',COALESCE(p.transactions,'[]'::jsonb))
       ORDER BY r.last_seen_at DESC),'[]'::jsonb)
       FROM ebay_offer_reference r LEFT JOIN ebay_purchase_history_check p
       ON p.ebay_item_id=r.ebay_item_id
       WHERE r.language_code='de' AND r.card_id='"""+card_id+"';"
    output=subprocess.run(['docker','exec','cardyssey-db','psql','-X','-U','cardyssey','-d','cardyssey','-At','-c',sql],capture_output=True,text=True,timeout=15,check=True)
    offers=json.loads(output.stdout.strip() or '[]')
    # Purchase-history tables often refer to entirely different cards. Those
    # rows are useful to the price collector, but not this card's admin queue.
    number=int(card['local_id']) if str(card.get('local_id','')).isdigit() else None
    denominator=int(card.get('denominator',128))
    for offer in offers:
        rows=offer.get('transactions') or []
        relevant_purchases=[]
        for transaction in rows:
            selection=transaction.get('variant','')
            exact=re.search(r'(?<![\w/])0*(\d{1,3})\s*/\s*0*(\d{2,3})(?!\w)',selection)
            if exact and number is not None and int(exact[1])==number and int(exact[2])==denominator and all(
                re.search(r'(?<!\w)'+re.escape(token)+r'(?!\w)',selection,re.I)
                for token in card['name'].split()):
                relevant_purchases.append(transaction)
        offer['transactions']=relevant_purchases
        offer['otherCardPurchasesHidden']=len(rows)-len(relevant_purchases)
    return {'cardId':card_id,'run':file.parents[1].name,
        'query':report.get('config',{}).get('query'),
        'totalSearchResults':len(results),'irrelevantCount':counts['OTHER_CARD'],
        'reviewableCount':len(relevant),'counts':counts,'results':relevant,
        'offers':offers,'purchaseAudit':report.get('purchaseHistoryAudit',{})}

if __name__=='__main__':
    try:print(json.dumps(evidence(sys.argv[1]),ensure_ascii=False))
    except (ValueError,FileNotFoundError,IndexError):
        print(json.dumps({'error':'no_saved_report'}));sys.exit(2)
