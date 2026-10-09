#!/usr/bin/env python3
"""Verified Korean single-card retail offers and their ordinary print variant.

No Japanese prices/images are copied. Import only an exact, in-stock Korean
listing with matching set/number/rarity and independently checked species names.
"""
import argparse
import concurrent.futures
import csv
import importlib.util
import io
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

def module(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

hydration=module('store-hydration')
retail=module('resolve-zhtw-retailer-prices')
HOST='https://uturitrading.com'
COLLECTION=HOST+'/en/collections/cartes-unite-pokemon'
SOURCE='WEB_UTURI_KO'
TRUSTED_KOREAN_SOURCES = frozenset(('WEB_UTURI_KO', 'WEB_MEWTWO_KO'))
SKU=re.compile(r'^(\d+)\s+((?:SV|SM|S\d|XY|BW|M\d)[A-Za-z0-9-]*)$',re.I)
VARIANT={'id':'generated','type':'normal','size':'standard','stamps':[],'legacyVariant':'NORMAL'}

def normalize(value):
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',str(value))).casefold()

def get_text(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Cardyssey/0.3 public-price-audit'}),timeout=12) as response:
        return response.read().decode('utf-8')

def species_names():
    text=get_text('https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon_species_names.csv')
    grouped=defaultdict(dict)
    for row in csv.DictReader(io.StringIO(text)):
        if row['local_language_id'] in ('3','6','9'):
            grouped[row['pokemon_species_id']][row['local_language_id']]=row['name']
    return [names for names in grouped.values() if all(k in names for k in ('3','6','9'))]

def get_collection():
    url=COLLECTION;seen=set();products={};deadline=time.monotonic()+130
    for page in range(1,81):
        if time.monotonic()>deadline:raise TimeoutError('collection deadline')
        data=hydration.loader_data(get_text(url))
        collection=next(v['collection'] for k,v in data.items() if 'collections.' in k and isinstance(v,dict))
        if collection.get('handle')!='cartes-unite-pokemon':raise ValueError('collection identity')
        batch=collection['products']
        for product in batch['nodes']:products[product['id']]=product
        print(json.dumps({'page':page,'products':len(products),'available':sum(p.get('availableForSale') is True for p in products.values())}),flush=True)
        info=batch['pageInfo']
        if info.get('hasNextPage') is False:return list(products.values())
        cursor=info.get('endCursor')
        if not cursor or cursor in seen:raise ValueError('invalid pagination')
        seen.add(cursor)
        url=COLLECTION+'?'+urllib.parse.urlencode({'direction':'next','cursor':cursor})
    raise ValueError('collection pagination limit')

def get_product(handle):
    if not re.fullmatch(r'[a-z0-9-]+',handle):raise ValueError('product handle')
    url=HOST+'/en/products/'+handle
    html=get_text(url)
    data=hydration.loader_data(html)
    product=next(v['product'] for k,v in data.items() if 'products.$handle' in k and isinstance(v,dict))
    if product.get('handle')!=handle:raise ValueError('product identity')
    ld=[]
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',html,re.S):
        obj=json.loads(block)
        if isinstance(obj,dict) and obj.get('@type')=='Product':ld.append(obj)
    if len(ld)!=1:raise ValueError('product structured data')
    return product,ld[0],url

def match_offer(row,product,ld,url,names):
    if row['language_code']!='ko' or row['identity_count']!=1:return None,'catalog_identity'
    if not row['card_id'].startswith('official_ko_'):return None,'catalog_identity'
    variant=product.get('selectedOrFirstAvailableVariant') or {}
    sku=SKU.fullmatch(str(variant.get('sku','')))
    if not sku or int(sku[1])!=int(row['local_id']) or normalize(sku[2])!=normalize(row['set_id']):return None,'set_number'
    if normalize((product.get('setCodeCustom') or {}).get('value',''))!=normalize(row['set_id']):return None,'set'
    if normalize((product.get('langueCustom') or {}).get('value','')) not in ('coréen','korean','ko','kr'):return None,'language'
    if product.get('vendor')!='Pokémon' or product.get('productType')!="Carte à l'unité":return None,'product_type'
    tags=product.get('tags') or []
    rarities=[tag.split(':',1)[1] for tag in tags if tag.startswith('Rareté:')]
    if len(rarities)!=1 or rarities[0]!=row['rarity'] or row['rarity'] not in ('C','U','R','RR','RRR','AR','SR','SAR','UR','HR','S','SSR'):return None,'rarity'
    text=' '.join(tags+[product.get('title','')])
    if re.search(r'promo|master.?ball|pok[eé].?ball|reverse|stamp|graded|PSA|BGS|CGC|1st.?edition',text,re.I):return None,'printing'
    english=[tag.split(':',1)[1] for tag in tags if tag.startswith('NomEN:')]
    if len(english)!=1:return None,'species'
    matches=[n for n in names if re.search(r'(?<![A-Za-z0-9])'+re.escape(n['9'])+r'(?![A-Za-z0-9])',english[0],re.I)]
    if not matches:return None,'species'
    longest=max(len(n['9']) for n in matches);matches=[n for n in matches if len(n['9'])==longest]
    if len(matches)!=1:return None,'species'
    name=matches[0]
    if normalize(name['6'])!=normalize(row['german_species']) or normalize(name['3']) not in normalize(row['native_name']):return None,'species'
    options=product.get('options') or []
    if len(options)!=1 or options[0].get('name')!='Title' or [v.get('name') for v in options[0].get('optionValues',[])]!=['Default Title']:return None,'variant'
    if product.get('adjacentVariants') or variant.get('title')!='Default Title' or variant.get('selectedOptions')!=[{'name':'Title','value':'Default Title'}]:return None,'variant'
    if variant.get('availableForSale') is not True:return None,'stock'
    offer=ld.get('offers') or {};price=variant.get('price') or {}
    if offer.get('availability')!='https://schema.org/InStock':return None,'stock'
    if ld.get('itemCondition')!='https://schema.org/NewCondition':return None,'condition'
    if price.get('currencyCode')!='EUR' or offer.get('priceCurrency')!='EUR':return None,'currency'
    amount=retail.positive_decimal(price.get('amount'))
    if amount is None or amount!=retail.positive_decimal(offer.get('price')):return None,'price'
    if ld.get('url')!=url or offer.get('url')!=url:return None,'product_identity'
    return dict(source=SOURCE,currency='EUR',amount=str(amount),title=product['title'],url=url,
                product_id=product['id'],offer_variant_id=variant['id'],rarity=rarities[0],condition='new/near-mint'),None

def load_targets(source=SOURCE):
    if source not in TRUSTED_KOREAN_SOURCES:raise ValueError('unsupported Korean source')
    sql="""WITH counts AS (SELECT set_id,LTRIM(local_id,'0') AS num,COUNT(*) AS identity_count
      FROM catalog_cards_mirror WHERE language_code='ko' GROUP BY set_id,LTRIM(local_id,'0'))
    SELECT COALESCE(jsonb_agg(row_to_json(t)),'[]') FROM (
      SELECT c.card_id,c.language_code,c.set_id,c.local_id,c.raw_payload->>'name' AS native_name,
      c.image_source_url,c.variants AS old_variants,c.rarity,counts.identity_count,
      species.german_species,p.updated_at AS old_updated,p.resolution_status AS old_status
      FROM catalog_cards_mirror c JOIN counts ON counts.set_id=c.set_id AND counts.num=LTRIM(c.local_id,'0')
      LEFT JOIN tcg_price_cache p ON p.card_id=c.card_id AND p.language_code=c.language_code AND p.variant_id='generated'
      JOIN LATERAL (SELECT MIN(german_species_name) AS german_species FROM catalog_supplemental_cards s
        WHERE s.canonical_card_id=c.card_id AND s.language_code=c.language_code HAVING COUNT(DISTINCT german_species_name)=1) species ON TRUE
      WHERE c.language_code='ko' AND c.details_complete AND c.local_id ~ '^[0-9]+$'
      AND c.image_source_url IS NOT NULL AND c.image_source_url<>''
      AND (COALESCE(jsonb_array_length(c.variants),0)=0 OR (c.variants='"""+json.dumps([VARIANT])+"""'::jsonb AND c.raw_payload->>'_cardyssey_retail_variant_source'='WEB_UTURI_KO'))
      AND (p.card_id IS NULL OR p.resolution_status='NO_PRICE' OR (p.source='WEB_UTURI_KO' AND (p.next_attempt_at<=NOW() OR p.updated_at<=NOW()-INTERVAL '6 days')))
    ) t;"""
    sql=sql.replace(retail.quote(SOURCE),retail.quote(source))
    return json.loads(retail.db(sql))

def apply_updates(updates, source=SOURCE):
    if source not in TRUSTED_KOREAN_SOURCES:raise ValueError('unsupported Korean source')
    if any(u['offer'].get('source')!=source for u in updates):raise ValueError('mixed Korean sources')
    if any(u['row'].get('language_code')!='ko' or not u['row']['card_id'].startswith('official_ko_') for u in updates):raise ValueError('unsupported Korean catalogue identity')
    if not updates:return dict(variants=0,prices=0,history=0)
    def q(value):return 'NULL' if value is None else retail.quote(value)
    values=[]
    for update in updates:
        r,o=update['row'],update['offer']
        detail=json.dumps(dict(o,basis='ASKING',in_stock=True,observed_at=update['observed_at'],nm_base_factor='0.92'),ensure_ascii=False)
        values.append('('+','.join(map(q,[r['card_id'],r['set_id'],r['local_id'],r['native_name'],r['image_source_url'],json.dumps(r['old_variants']),r['old_updated'],r['old_status'],update['base_eur'],detail]))+')')
    sql="""WITH incoming(card_id,set_id,local_id,native_name,image,old_variants,old_updated,old_status,base_eur,detail) AS (VALUES """+','.join(values)+"""),
    eligible AS (SELECT i.*,jsonb_array_length(c.variants)=0 AS needs_variant FROM incoming i
      JOIN catalog_cards_mirror c ON c.card_id=i.card_id AND c.language_code='ko'
      LEFT JOIN tcg_price_cache p ON p.card_id=c.card_id AND p.language_code='ko' AND p.variant_id='generated'
      WHERE c.set_id=i.set_id AND c.local_id=i.local_id AND c.raw_payload->>'name'=i.native_name AND c.image_source_url=i.image
      AND c.variants=i.old_variants::jsonb AND p.updated_at IS NOT DISTINCT FROM i.old_updated::timestamptz
      AND p.resolution_status IS NOT DISTINCT FROM i.old_status),
    catalog_changed AS (UPDATE catalog_cards_mirror c SET variants='"""+json.dumps([VARIANT])+"""'::jsonb,
      raw_payload=jsonb_set(c.raw_payload,'{_cardyssey_retail_variant_source}','\"WEB_UTURI_KO\"'::jsonb,true)
      FROM eligible i WHERE i.needs_variant AND c.language_code='ko' AND c.card_id=i.card_id
      AND c.variants=i.old_variants::jsonb AND c.set_id=i.set_id AND c.local_id=i.local_id
      AND c.raw_payload->>'name'=i.native_name AND c.image_source_url=i.image RETURNING c.card_id),
    ready AS (SELECT e.* FROM eligible e WHERE NOT e.needs_variant OR EXISTS(SELECT 1 FROM catalog_changed c WHERE c.card_id=e.card_id)),
    written AS (INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,source,base_eur,updated_at,resolution_status,failure_detail,next_attempt_at)
      SELECT card_id,'ko','generated','NORMAL','WEB_UTURI_KO',base_eur::numeric,NOW(),'PRICE_FOUND',detail,NOW()+INTERVAL '7 days' FROM ready
      ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,
      updated_at=EXCLUDED.updated_at,resolution_status=EXCLUDED.resolution_status,failure_detail=EXCLUDED.failure_detail,next_attempt_at=EXCLUDED.next_attempt_at
      WHERE EXISTS(SELECT 1 FROM ready r WHERE r.card_id=EXCLUDED.card_id
        AND tcg_price_cache.updated_at IS NOT DISTINCT FROM r.old_updated::timestamptz
        AND tcg_price_cache.resolution_status IS NOT DISTINCT FROM r.old_status)
      RETURNING card_id,language_code,variant_id,source,base_eur),
    history AS (INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at)
      SELECT card_id,language_code,variant_id,source,base_eur,NOW() FROM written RETURNING 1)
    SELECT jsonb_build_object('variants',(SELECT COUNT(*) FROM catalog_changed),'prices',(SELECT COUNT(*) FROM written),'history',(SELECT COUNT(*) FROM history));"""
    sql=sql.replace(retail.quote(SOURCE),retail.quote(source))
    sql=sql.replace(retail.quote(json.dumps(SOURCE)),retail.quote(json.dumps(source)))
    return json.loads(retail.db(sql))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--report',type=Path)
    args=parser.parse_args();rows=load_targets();by_key=defaultdict(list)
    for row in rows:by_key[(normalize(row['set_id']),int(row['local_id']))].append(row)
    products=get_collection();names=species_names();candidates=[];rejected=Counter();errors=[]
    for product in products:
        if product.get('availableForSale') is not True:continue
        match=re.search(r'(\d+)\s+((?:SV|SM|S\d|XY|BW|M\d)[A-Za-z0-9-]*)$',product.get('title',''),re.I)
        if match and (normalize(match[2]),int(match[1])) in by_key:candidates.append(product)
    def fetch(p):
        try:return p,get_product(p['handle']),None
        except Exception as e:return p,None,type(e).__name__+': '+str(e)
    updates=[];observed=datetime.now(timezone.utc).isoformat();seen=set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for original,result,error in pool.map(fetch,candidates):
            if error:errors.append(dict(handle=original['handle'],error=error));continue
            product,ld,url=result;sku=SKU.fullmatch(str((product.get('selectedOrFirstAvailableVariant') or {}).get('sku','')))
            if not sku:rejected['sku']+=1;continue
            for row in by_key[(normalize(sku[2]),int(sku[1]))]:
                offer,reason=match_offer(row,product,ld,url,names)
                if not offer:rejected[reason]+=1;continue
                if row['card_id'] in seen:raise ValueError('ambiguous duplicate retail identity')
                seen.add(row['card_id']);base=(Decimal(offer['amount'])/Decimal('0.92')).quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP)
                updates.append(dict(row=row,offer=offer,base_eur=str(base),observed_at=observed))
    report=dict(catalog_candidates=len(rows),retail_products=len(products),product_candidates=len(candidates),updates=updates,rejected=dict(rejected),errors=errors)
    report['applied']=apply_updates(updates) if args.apply and not errors else dict(variants=0,prices=0,history=0)
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='updates'}|{'matched':len(updates)},ensure_ascii=False),flush=True)
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
