#!/usr/bin/env python3
"""Exact Japanese editions and numbered promos, in stock and shop condition A."""
import argparse
import concurrent.futures
import importlib.util
import json
import re
import urllib.request
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path

spec=importlib.util.spec_from_file_location('retail',Path(__file__).with_name('resolve-zhtw-retailer-prices.py'))
retail=importlib.util.module_from_spec(spec);spec.loader.exec_module(retail)
SOURCE='WEB_HARERUYA_JP'
HOST='https://www.hareruya2.com'
# A lone high asking price is insufficient for an automatic collection valuation.
# Keep exact public evidence in the report for independent/manual review.
MAX_SINGLE_ASK_EUR=Decimal('100')

def needs_price_review(offer,fx):
 return Decimal(offer['amount'])*fx>MAX_SINGLE_ASK_EUR
MANIFEST={
 'PCG1':('74','P1'),'PCG2':('75','P2'),'PCG3':('76','P3'),'PCG4':('77','P4'),
 'PCG5':('78','P5'),'PCG6':('79','P6'),'PCG7':('80','P7'),'PCG8':('81','P8'),'PCG9':('82','P9'),
 'E1':('49','e1'),'E2':('50','e2'),'E3':('51','e3'),'E4':('52','e4'),'E5':('53','e5'),'VS1':('45','VS'),'web1':('47','web'),
 'SV-P':('581','SV-P'),'M-P':('699','M-P'),
}
TITLE=re.compile(r'^(.+)\(([^)]+)\)\{[^}]+\}〈(\d+)/(\d+|SV-P|M-P)〉\[([A-Za-z0-9-]+)\]$')

def fetch_set(item):
 code,(handle,printed)=item;products=[];seen=set()
 try:
  for page in range(1,5):
   batch=retail.get_json(f'{HOST}/collections/{handle}/products.json?limit=250&page={page}')['products']
   for product in batch:
    if product['id'] in seen:raise ValueError('repeated pagination')
    seen.add(product['id']);products.append(product)
   if len(batch)<250:return code,products,None
  return code,[],'pagination_limit'
 except Exception as e:return code,[],type(e).__name__+': '+str(e)

def edition(variant,all_variants):
 if variant.get('foil') or variant.get('size','standard') not in ('standard',None) or variant.get('legacyVariant') not in ('NORMAL','HOLO'):return None
 stamps=variant.get('stamps') or [];subtype=variant.get('subtype')
 if stamps and all('1st' in str(s).lower() for s in stamps) and not subtype:return 'first'
 if not stamps and subtype=='unlimited':return 'unlimited'
 if not stamps and not subtype and any(any('1st' in str(s).lower() for s in v.get('stamps',[])) for v in all_variants) and not any(v.get('subtype')=='unlimited' for v in all_variants):return 'unlimited'
 return None

def match_offer(row,product):
 title=product.get('title','');match=TITLE.fullmatch(title)
 if not match or '状態' in title:return None,'title_or_condition'
 head,rarity,number,total,code=match.groups()
 if row['language_code']!='ja' or code.casefold()!=MANIFEST[row['set_id']][1].casefold():return None,'set_language'
 promo=row['set_id'] in ('SV-P','M-P')
 if int(number)!=int(row['local_id']):return None,'number'
 if promo:
  if total!=row['set_id'] or rarity!='PROMO':return None,'promo_set'
  variant=row['variant']
  if (row['legacy_variant']!='NORMAL' or variant.get('type')!='normal'
      or variant.get('size','standard') not in ('standard',None)
      or any(variant.get(k) for k in ('foil','stamps','subtype'))
      or len(row['all_variants'])!=1):return None,'promo_variant'
  # Exact full title is essential for Trainers/Energy without species metadata.
  if retail.normalize(head)!=retail.normalize(row['native_name'] or row['name']):return None,'name'
 elif not total.isdigit() or int(total)!=row['official_count']:return None,'number'
 first=bool(re.search(r'1ED|初版',head));unlimited=bool(re.search(r'再販|再版',head))
 if not promo and first==unlimited:return None,'unmarked_edition'
 expected=edition(row['variant'],row['all_variants'])
 if not promo and expected!=('first' if first else 'unlimited'):return None,'edition'
 # Reject multiple foil choices for the same edition unless the shop explicitly labels the foil.
 candidates=[v for v in row['all_variants'] if edition(v,row['all_variants'])==expected]
 foil=bool('キラ' in head or rarity.endswith('H'))
 if foil:
  if row['legacy_variant']!='HOLO':return None,'foil'
 elif not promo and len(candidates)!=1:return None,'ambiguous_foil'
 body=product.get('body_html','')
 if '状態表記の無いカードは状態A' not in body:return None,'condition'
 variants=product.get('variants') or []
 if len(variants)!=1 or variants[0].get('title')!='Default Title':return None,'retailer_variant'
 v=variants[0]
 if v.get('available') is not True:return None,'stock'
 price=retail.positive_decimal(v.get('price'))
 if price is None:return None,'price'
 names=re.findall(r'(?:名前|英語名)：([^<\n]+)',body)
 raw=row['native_name'] or row['name']
 native_match=promo or any(retail.normalize(name) in retail.normalize(raw) for name in names if name.strip())
 english=re.search(r'英語名：([^<\n]+)',body)
 blueprint_match=bool(english and row.get('blueprint_name') and re.search(r'(?<![A-Za-z0-9])'+re.escape(english[1].strip())+r'(?![A-Za-z0-9])',row['blueprint_name'],re.I))
 if not native_match and not blueprint_match:return None,'name'
 handle=str(product.get('handle',''))
 if not re.fullmatch(r'[a-z0-9-]+',handle):return None,'product_identity'
 return dict(source=SOURCE,currency='JPY',amount=str(price),title=title,url=HOST+'/products/'+handle,
             product_id=product['id'],offer_variant_id=v['id'],condition='Hareruya condition A',
             identity_method=('exact-numbered-promo-native-title' if promo else 'native-name') if native_match else 'exact-edition-blueprint-species',blueprint_id=row.get('blueprint_id') if not native_match else None),None

def load_targets():
 return json.loads(retail.db("""SELECT COALESCE(jsonb_agg(row_to_json(t)),'[]') FROM (
 SELECT p.card_id,p.language_code,p.variant_id,p.legacy_variant,p.resolution_status,p.updated_at,
 c.set_id,c.local_id,c.name,c.raw_payload->>'name' AS native_name,c.variants AS all_variants,
 v.value AS variant,s.official_count,vi.blueprint_id,vi.expansion_id,vi.method AS identity_method
 FROM tcg_price_cache p JOIN catalog_cards_mirror c USING(card_id,language_code)
 JOIN catalog_sets_mirror s USING(set_id,language_code)
 CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
 LEFT JOIN cardtrader_variant_identity_cache vi ON vi.card_id=p.card_id AND vi.language_code=p.language_code AND vi.variant_id=p.variant_id
 WHERE p.language_code='ja' AND p.variant_id=v.value->>'id' AND c.local_id ~ '^[0-9]+$'
 AND LEFT(c.card_id,9)<>'official_' AND
 (p.resolution_status='NO_PRICE' OR (p.source='WEB_HARERUYA_JP' AND (p.next_attempt_at<=NOW() OR p.updated_at<=NOW()-INTERVAL '6 days')))
 ) t;"""))

def verified_blueprint_names(rows):
 token=""
 for line in Path('/home/tv/cardshop/platform/.env').read_text().splitlines():
  if line.startswith('CARDTRADER_API_TOKEN='):token=line.split('=',1)[1].strip();break
 if not token:return {},['CardTrader identity verification not configured']
 eligible=[r for r in rows if r.get('blueprint_id') and r.get('expansion_id') and
   r.get('identity_method')=='ja-classic-'+('1st' if edition(r['variant'],r['all_variants'])=='first' else 'unlimited')]
 wanted={r['blueprint_id']:r for r in eligible};verified={};warnings=[]
 def fetch(eid):
  try:
   request=urllib.request.Request(f'https://api.cardtrader.com/api/v2/blueprints/export?expansion_id={eid}',headers={'Authorization':'Bearer '+token,'Accept':'application/json','User-Agent':'Cardyssey/0.3 identity-audit'})
   with urllib.request.urlopen(request,timeout=15) as response:return eid,json.load(response),None
  except Exception as e:return eid,[],type(e).__name__+': '+str(e)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for eid,blueprints,error in pool.map(fetch,sorted({r['expansion_id'] for r in eligible})):
   if error:warnings.append(dict(expansion=eid,error=error));continue
   for bp in blueprints:
    row=wanted.get(bp.get('id'))
    if not row or row['expansion_id']!=eid:continue
    number=str((bp.get('fixed_properties') or {}).get('collector_number','')).split('/',1)[0].strip()
    if number.isdigit() and int(number)==int(row['local_id']) and isinstance(bp.get('name'),str):verified[bp['id']]=bp['name']
 return verified,warnings

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--report',type=Path)
 args=parser.parse_args();rows=[r for r in load_targets() if r['set_id'] in MANIFEST];by_key=defaultdict(list)
 for row in rows:by_key[(row['set_id'],int(row['local_id']))].append(row)
 if retail.get_json(HOST+'/cart.js').get('currency')!='JPY':raise SystemExit('Unverified retailer currency')
 fx_data=retail.get_json('https://api.frankfurter.dev/v2/rate/JPY/EUR');fx=retail.positive_decimal(fx_data.get('rate'))
 if fx is None or not fx_data.get('date'):raise SystemExit('FX unavailable')
 errors=[];updates=[];review=[];rejected=Counter();observed=datetime.now(timezone.utc).isoformat();verified={};seen=set()
 products_by_set={};needed=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for set_id,products,error in pool.map(fetch_set,[(k,MANIFEST[k]) for k in sorted({r['set_id'] for r in rows})]):
   if error:errors.append(dict(set=set_id,error=error));continue
   products_by_set[set_id]=products
   for product in products:
    title=TITLE.fullmatch(product.get('title',''))
    if title:
     for row in by_key[(set_id,int(title[3]))]:
      if match_offer(row,product)[1]=='name':needed.append(row)
 bp_names,identity_warnings=verified_blueprint_names(needed) if needed else ({},[])
 for row in rows:row['blueprint_name']=bp_names.get(row.get('blueprint_id'))
 for set_id,products in products_by_set.items():
   for product in products:
    title=TITLE.fullmatch(product.get('title',''))
    if not title:continue
    for row in by_key[(set_id,int(title[3]))]:
     offer,reason=match_offer(row,product)
     if not offer:rejected[reason]+=1;continue
     # Product JSON provides explicit major-unit currency; don't assume Ajax minor units.
     if offer['product_id'] not in verified:
      detail=retail.get_json(offer['url']+'.json')['product'];vs=detail.get('variants',[])
      verified[offer['product_id']]=len(vs)==1 and vs[0].get('id')==offer['offer_variant_id'] and vs[0].get('price_currency')=='JPY' and retail.positive_decimal(vs[0].get('price'))==Decimal(offer['amount'])
     if not verified[offer['product_id']]:rejected['currency_units']+=1;continue
     identity=(row['card_id'],row['variant_id'])
     if identity in seen:raise ValueError('multiple indistinguishable offers')
     seen.add(identity);base=(Decimal(offer['amount'])*fx/retail.NM_FACTOR).quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP)
     update=dict(row=row,offer=offer,base_eur=str(base),fx=str(fx),fx_date=fx_data['date'],observed_at=observed)
     if needs_price_review(offer,fx):
      review.append(update|{'reason':'Single asking offer exceeds EUR 100; independent valuation review required'});continue
     updates.append(update)
   print(json.dumps({'set':set_id,'products':len(products),'matched_total':len(updates)}),flush=True)
 report=dict(candidates=len(rows),updates=updates,review=review,rejected=dict(rejected),errors=errors,identity_warnings=identity_warnings,applied=retail.apply_updates(updates) if args.apply and not errors else 0)
 if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('updates','review')}|{'matched':len(updates),'review_count':len(review)},ensure_ascii=False))
 if errors:raise SystemExit(1)

if __name__=='__main__':main()
