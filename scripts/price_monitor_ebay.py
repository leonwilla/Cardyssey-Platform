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
history_stats={}
try:
 history_sql="SELECT card_id,count(*),count(*) FILTER (WHERE evidence_type='EBAY_PURCHASE_HISTORY'),max(sold_on) FROM ebay_sold_history WHERE language_code='de' GROUP BY card_id"
 history_out=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',history_sql],timeout=12,text=True)
 for line in history_out.splitlines():
  parts=line.split('|',3)
  if len(parts)==4:
   history_stats[parts[0]]=dict(totalHistoricalSales=int(parts[1]),purchaseHistorySales=int(parts[2]),latestRecordedSale=parts[3])
except (subprocess.CalledProcessError,subprocess.TimeoutExpired,ValueError):pass
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
# Bulk cards remain visible on the TCG tab, not the rare/special eBay queue.
# Do not delete existing eBay observations or previously reviewed evidence.
bulk_raw=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-Atc',"SELECT card_id FROM catalog_cards_mirror WHERE language_code='de' AND lower(trim(rarity)) IN ('häufig','ungewöhnlich','common','uncommon','c','u','rare_c','rare_u','rare_c_c','rare_u_c','one diamond','two diamond','une diamant','deux diamant');"],timeout=15,text=True)
bulk_ids=set(bulk_raw.splitlines())
for card_id,c in cards.items():
 if card_id in bulk_ids:continue
 r=results.get(card_id,{});price=prices.get(card_id)
 review=reviews.get(card_id,{'status':'AUTO','refreshDays':7,'showOfferReferences':True,'note':''})
 offers=references.get(card_id,[])
 audit=r.get('purchaseHistoryAudit') or {}
 reasons=[]
 if r.get('status') in ('FETCH_INCOMPLETE','STOPPED_SERVICE_ERRORS'):reasons.append('eBay-Abruf fehlgeschlagen')
 if r.get('status') in ('CATALOG_VARIANT_REVIEW','SET_NUMBER_REVIEW'):reasons.append('Druckvariante prüfen')
 if audit.get('unpriced',0)>0:reasons.append('Diese Karte verkauft, aber bezahlter Preis unbekannt')
 if audit.get('unpriced_other_card',0)>0 or any(x.get('purchaseHistoryStatus')=='NO_VISIBLE_PRICE' for x in offers):reasons.append('Auswahlangebot mit Transaktionen ohne sichtbaren Kaufpreis (ggf. andere Karte)')
 if offers and not price:reasons.append('Auswahlangebote ohne bestätigten Kartenpreis')
 if price and price[1]<3:reasons.append('Median mit weniger als 3 Verkäufen')
 if not price and not reasons:reasons.append('Noch kein verifizierter eBay-Verkauf')
 snoozed=False
 if review.get('status') in ('NO_VERIFIED_SALE','VERIFIED') and review.get('updatedAt'):
  try:
   updated=datetime.fromisoformat(review['updatedAt'].replace(' ','T'))
   if updated.tzinfo is None:updated=updated.replace(tzinfo=timezone.utc)
   snoozed=datetime.now(timezone.utc)-updated<timedelta(days=review.get('refreshDays',7))
  except (ValueError,TypeError):pass
 requires_review=bool(reasons) and not snoozed
 items.append({'cardId':card_id,'setId':c['set_id'],'name':c['name'],'number':c['local_id'],'price':price[0] if price else None,'sales':price[1] if price else None,'updatedAt':price[2] if price else None,'status':'PRICE_FOUND' if price else r.get('status','NOT_CHECKED'),'failure':None if price else r.get('status','Noch nicht geprüft'),'searchQuery':r.get('query'),'parsed':r.get('parsed',0),'matched':r.get('nm_candidates',0),'rejections':r.get('rejections',{}),'collectorReasons':r.get('collectorReasons',{}),'run':r.get('run'),'pages':r.get('pages',[]),'imageCandidates':r.get('imageCandidates',[]),'purchaseHistoryAudit':r.get('purchaseHistoryAudit',{}),'historyStats':history_stats.get(card_id,{'totalHistoricalSales':0,'purchaseHistorySales':0,'latestRecordedSale':None}),'review':review,'offerReferences':offers,'reviewRequired':requires_review,'reviewReasons':reasons,'snoozed':snoozed})
catalog_sql="SELECT set_id,count(*) FROM catalog_cards_mirror WHERE language_code='de' AND set_id IN ('30th','30th-c','mep','sv01','sv02') GROUP BY set_id"
catalog_out=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',catalog_sql],timeout=12,text=True)
catalog_counts={setid:int(count) for line in catalog_out.splitlines() if '|' in line for setid,count in [line.split('|',1)]}
bulk_sql="SELECT set_id,count(*) FROM catalog_cards_mirror WHERE language_code='de' AND lower(trim(rarity)) IN ('häufig','ungewöhnlich','common','uncommon','c','u','rare_c','rare_u','rare_c_c','rare_u_c','one diamond','two diamond','une diamant','deux diamant') AND set_id IN ('30th','30th-c','mep','sv01','sv02') GROUP BY set_id"
bulk_counts_raw=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',bulk_sql],timeout=12,text=True)
bulk_counts={setid:int(count) for line in bulk_counts_raw.splitlines() if '|' in line for setid,count in [line.split('|',1)]}
for setid,count in bulk_counts.items():catalog_counts[setid]=max(0,catalog_counts.get(setid,0)-count)
# eBay MEP group covers only anniversary-related 094–101, not the entire promo series.
catalog_counts['mep']=8
# Report eBay coverage separately from fallback reference prices.
fallback_sql="""SELECT c.set_id,count(*) FROM catalog_cards_mirror c WHERE c.language_code='de'
 AND c.set_id IN ('30th','30th-c','mep','sv01','sv02')
 AND lower(trim(COALESCE(c.rarity,''))) NOT IN ('häufig','ungewöhnlich','common','uncommon','c','u','rare_c','rare_u','rare_c_c','rare_u_c','one diamond','two diamond','une diamant','deux diamant')
 AND (c.set_id <> 'mep' OR c.local_id BETWEEN '094' AND '101')
 AND EXISTS (SELECT 1 FROM tcg_price_cache t WHERE t.card_id=c.card_id
             AND t.language_code=c.language_code AND t.base_eur>0)
 GROUP BY c.set_id"""
fallback_out=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',fallback_sql],timeout=12,text=True)
fallback_counts={setid:int(count) for line in fallback_out.splitlines() if '|' in line for setid,count in [line.split('|',1)]}
print(json.dumps({'catalogCounts':catalog_counts,'bulkCounts':bulk_counts,'fallbackCounts':fallback_counts,'items':items,'runs':[{'name':p.name,'status':json.loads((p/'progress.json').read_text()).get('status')} for p in runs]},ensure_ascii=False))
