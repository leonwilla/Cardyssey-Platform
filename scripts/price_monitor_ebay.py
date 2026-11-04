#!/usr/bin/env python3
"""Read only eBay monitor. Preserve every batch, prefer most recent results."""
import json,sys,subprocess
from datetime import datetime,timezone,timedelta
from pathlib import Path
root=Path('/home/tv/cardyssey-ebay-collector')
runs=sorted((p for p in [*root.glob('anniversary-*'),*root.glob('admin-set-runs/*')]
             if (p/'progress.json').is_file()),key=lambda p:p.stat().st_mtime)
cards={}; results={}
for run in runs:
 manifest=run/'manifest.json'
 if manifest.is_file():
  for c in json.loads(manifest.read_text()):cards[c['card_id']]=c
 state=json.loads((run/'progress.json').read_text())
 for r in state.get('results',[]):
  detail={**r,'run':run.name}
  p=run/r['card_id']/'sales.json'
  if p.is_file():
   report=json.loads(p.read_text())
   detail['query']=report.get('config',{}).get('query') or report.get('query')
   detail['collectorReasons']={}
   from collections import Counter
   reasons=Counter()
   for row in report.get('rows',[]):
    if not row.get('eligible'):
     reasons.update(filter(None,(row.get('exclusions') or '').split(';')))
   detail['collectorReasons']=dict(reasons)
   detail['pages']=report.get('pages',[])
   detail['purchaseHistoryAudit']=report.get('purchaseHistoryAudit',{})
   # Candidate photos are evidence for human/image-assist review, not proof.
   detail['imageCandidates']=[{'title':row.get('title','')[:160],
       'imageUrl':row.get('image_url'), 'listingUrl':row.get('url'),
       'exclusions':row.get('exclusions') or '', 'saleDate':row.get('sold_date'),
       'imageMatchScore':row.get('image_match_score'),
       'imageIdentityVerified':row.get('image_identity_verified') is True}
       for row in report.get('rows',[]) if row.get('image_url')][:8]

  results[r['card_id']]=detail
sql="SELECT card_id,round((base_eur*0.92)::numeric,4),sample_count,updated_at FROM ebay_price_cache WHERE language_code='de' AND source='CARDYSSEY_EBAY' AND base_eur>0"
out=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',sql],timeout=12,text=True)
prices={a:(float(b),int(c),t) for line in out.splitlines() if (parts:=line.split('|')) and len(parts)==4 for a,b,c,t in [parts]}
reviews={}
references={}
try:
 review_sql="SELECT card_id,review_status,refresh_days,show_offer_references,note,updated_at FROM ebay_card_review WHERE language_code='de'"
 review_out=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',review_sql],timeout=12,text=True)
 for line in review_out.splitlines():
  parts=line.split('|',5)
  if len(parts)==6:reviews[parts[0]]=dict(status=parts[1],refreshDays=int(parts[2]),showOfferReferences=parts[3]=='t',note=parts[4],updatedAt=parts[5])
 ref_sql="""SELECT card_id,COALESCE(jsonb_agg(jsonb_build_object(
      'title',title,'url',listing_url,'price',displayed_price_eur,'seenAt',last_seen_at,
      'itemId',ebay_item_id,'purchaseHistoryStatus',history_status,
      'purchaseRowsCount',history_count,'purchaseRows',purchase_rows)
      ORDER BY last_seen_at DESC),'[]')
    FROM (SELECT r.card_id,r.title,r.listing_url,r.displayed_price_eur,
      r.last_seen_at,r.ebay_item_id,p.status AS history_status,
      COALESCE(jsonb_array_length(p.transactions),0) AS history_count,
      COALESCE((SELECT jsonb_agg(value) FROM (
        SELECT value FROM jsonb_array_elements(p.transactions) AS value LIMIT 5) subset),'[]'::jsonb) AS purchase_rows,
      row_number() OVER (PARTITION BY r.card_id ORDER BY r.last_seen_at DESC) rank
      FROM ebay_offer_reference r LEFT JOIN ebay_purchase_history_check p
        ON p.ebay_item_id=r.ebay_item_id
      WHERE r.language_code='de' AND r.sale_for_card_confirmed=false) t
    WHERE rank<=6 GROUP BY card_id"""
 ref_out=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',ref_sql],timeout=12,text=True)
 for line in ref_out.splitlines():
  if '|' in line:
   card_id,data=line.split('|',1)
   references[card_id]=json.loads(data)
except (subprocess.CalledProcessError,subprocess.TimeoutExpired,ValueError):pass
items=[]
for card_id,c in cards.items():
 r=results.get(card_id,{});price=prices.get(card_id)
 review=reviews.get(card_id,{'status':'AUTO','refreshDays':7,'showOfferReferences':True,'note':''})
 offers=references.get(card_id,[])
 audit=r.get('purchaseHistoryAudit') or {}
 reasons=[]
 if r.get('status') in ('FETCH_INCOMPLETE','STOPPED_SERVICE_ERRORS'):reasons.append('eBay-Abruf fehlgeschlagen')
 if r.get('status') in ('CATALOG_VARIANT_REVIEW','SET_NUMBER_REVIEW'):reasons.append('Druckvariante prüfen')
 if audit.get('unpriced',0)>0 or any(x.get('purchaseHistoryStatus')=='NO_VISIBLE_PRICE' for x in offers):reasons.append('Verkauft, bezahlter Preis unbekannt')
 if offers and not price:reasons.append('Auswahlangebote ohne bestätigten Kartenpreis')
 if price and price[1]<3:reasons.append('Median mit weniger als 3 Verkäufen')
 if not price and not reasons:reasons.append('Noch kein verifizierter eBay-Verkauf')
 snoozed=False
 if review.get('status')=='NO_VERIFIED_SALE' and review.get('updatedAt'):
  try:
   updated=datetime.fromisoformat(review['updatedAt'].replace(' ','T'))
   if updated.tzinfo is None:updated=updated.replace(tzinfo=timezone.utc)
   snoozed=datetime.now(timezone.utc)-updated<timedelta(days=review.get('refreshDays',7))
  except (ValueError,TypeError):pass
 requires_review=bool(reasons) and not snoozed
 items.append({'cardId':card_id,'setId':c['set_id'],'name':c['name'],'number':c['local_id'],'price':price[0] if price else None,'sales':price[1] if price else None,'updatedAt':price[2] if price else None,'status':'PRICE_FOUND' if price else r.get('status','NOT_CHECKED'),'failure':None if price else r.get('status','Noch nicht geprüft'),'searchQuery':r.get('query'),'parsed':r.get('parsed',0),'matched':r.get('nm_candidates',0),'rejections':r.get('rejections',{}),'collectorReasons':r.get('collectorReasons',{}),'run':r.get('run'),'pages':r.get('pages',[]),'imageCandidates':r.get('imageCandidates',[]),'purchaseHistoryAudit':r.get('purchaseHistoryAudit',{}),'review':review,'offerReferences':offers,'reviewRequired':requires_review,'reviewReasons':reasons,'snoozed':snoozed})
catalog_sql="SELECT set_id,count(*) FROM catalog_cards_mirror WHERE language_code='de' AND set_id IN ('30th','30th-c','mep','sv01','sv02') GROUP BY set_id"
catalog_out=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',catalog_sql],timeout=12,text=True)
catalog_counts={setid:int(count) for line in catalog_out.splitlines() if '|' in line for setid,count in [line.split('|',1)]}
# eBay MEP group covers only anniversary-related 094–101, not the entire promo series.
catalog_counts['mep']=8
# Report eBay coverage separately from fallback reference prices.
fallback_sql="""SELECT c.set_id,count(*) FROM catalog_cards_mirror c WHERE c.language_code='de'
 AND c.set_id IN ('30th','30th-c','mep','sv01','sv02')
 AND (c.set_id <> 'mep' OR c.local_id BETWEEN '094' AND '101')
 AND EXISTS (SELECT 1 FROM tcg_price_cache t WHERE t.card_id=c.card_id
             AND t.language_code=c.language_code AND t.base_eur>0)
 GROUP BY c.set_id"""
fallback_out=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',fallback_sql],timeout=12,text=True)
fallback_counts={setid:int(count) for line in fallback_out.splitlines() if '|' in line for setid,count in [line.split('|',1)]}
print(json.dumps({'catalogCounts':catalog_counts,'fallbackCounts':fallback_counts,'items':items,'runs':[{'name':p.name,'status':json.loads((p/'progress.json').read_text()).get('status')} for p in runs]},ensure_ascii=False))
