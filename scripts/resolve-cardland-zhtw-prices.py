#!/usr/bin/env python3
"""Exact in-stock zh-TW single-card asking prices from CardLand's public store feed."""
import argparse
import concurrent.futures
import importlib.util
import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

spec = importlib.util.spec_from_file_location('retail', Path(__file__).with_name('resolve-zhtw-retailer-prices.py'))
retail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retail)
retail.SOURCES['cardland.com.hk'] = {'source':'WEB_CARDLAND_HK','collections':{}}
SKU = re.compile(r'^HK-([A-Za-z][A-Za-z0-9-]*)-(\d+)/(\d+)-(noth)-(\d+)$')
BASE = 'https://cardland.com.hk/wp-json/wc/store/v1/products'


def fetch_set(set_id):
    products, seen = [], set()
    try:
        for page in range(1, 9):
            url = BASE + '?' + urllib.parse.urlencode({
                'search':set_id,'category':4999,'per_page':100,'page':page,
            })
            request = urllib.request.Request(url,headers={
                'User-Agent':'Cardyssey/0.3 public-price-audit','Accept':'application/json',
            })
            with urllib.request.urlopen(request,timeout=12) as response:
                batch = json.load(response)
                total_pages = int(response.headers.get('X-WP-TotalPages','0'))
            if not isinstance(batch,list):
                raise ValueError('invalid public product feed')
            for product in batch:
                if product.get('id') in seen:
                    raise ValueError('repeated product/pagination')
                seen.add(product.get('id')); products.append(product)
            if len(batch)<100 or (total_pages and page>=total_pages):
                return set_id, products, None
        return set_id, [], 'pagination_limit'
    except Exception as error:
        return set_id, [], type(error).__name__+': '+str(error)


def match_offer(row,product):
    if not retail.eligible_variant(row):
        return None,'catalog_variant'
    sku = SKU.fullmatch(str(product.get('sku','')))
    if not sku:
        return None,'sku_or_printing'
    code,number,total,printing,product_id = sku.groups()
    if code.casefold()!=row['set_id'].casefold():
        return None,'set'
    if int(number)!=int(row['local_id']) or int(total)!=row['official_count']:
        return None,'number'
    if retail.normalize(product.get('name',''))!=retail.normalize(row['name']):
        return None,'name'
    if not any(c.get('id')==4999 and c.get('name')=='寶可夢繁中版卡 單卡專區'
               for c in product.get('categories',[])):
        return None,'language'
    if product.get('type')!='simple' or product.get('has_options') is not False or product.get('variations'):
        return None,'retailer_variant'
    if (product.get('is_in_stock') is not True or product.get('is_purchasable') is not True
            or product.get('is_on_backorder') is not False):
        return None,'stock'
    prices=product.get('prices') or {}
    if prices.get('currency_code')!='HKD':
        return None,'currency'
    minor=prices.get('currency_minor_unit')
    amount=str(prices.get('price',''))
    if type(minor) is not int or not 0<=minor<=3 or not re.fullmatch(r'\d+',amount):
        return None,'price_units'
    price=retail.positive_decimal(amount)
    if price is None:
        return None,'price'
    price=price/(Decimal(10)**minor)
    url=product.get('permalink','')
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.netloc!='cardland.com.hk' or not parsed.path.startswith('/product/'):
        return None,'product_identity'
    if str(product.get('id'))!=product_id:
        return None,'product_identity'
    return {'source':'WEB_CARDLAND_HK','hkd':str(price),'title':product['name'],
            'url':url,'product_id':product['id'],'offer_variant_id':None},None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    rows=retail.load_targets()
    fx_data=retail.get_json('https://api.frankfurter.dev/v2/rate/HKD/EUR')
    fx=retail.positive_decimal(fx_data.get('rate'))
    if fx is None or not fx_data.get('date'):
        raise SystemExit('HKD/EUR rate/date unavailable; no writes')
    by_set=defaultdict(list)
    for row in rows:by_set[row['set_id']].append(row)
    report={'candidates':len(rows),'errors':[],'updates':[],'rejected':{}}
    rejected=Counter()
    observed=datetime.now(timezone.utc).isoformat()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for set_id,products,error in pool.map(fetch_set,sorted(by_set)):
            if error:
                report['errors'].append({'set':set_id,'error':error});continue
            index=defaultdict(list)
            for product in products:
                sku=SKU.fullmatch(str(product.get('sku','')))
                if sku:index[int(sku[2])].append(product)
            matched=0
            for row in by_set[set_id]:
                offers=[]
                for product in index[int(row['local_id'])]:
                    offer,reason=match_offer(row,product)
                    if offer:offers.append(offer)
                    else:rejected[reason]+=1
                if not offers:continue
                chosen=min(offers,key=lambda offer:Decimal(offer['hkd']))
                base=(Decimal(chosen['hkd'])*fx/retail.NM_FACTOR).quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP)
                if base<=0:rejected['rounded_price']+=1;continue
                report['updates'].append({'row':row,'offer':chosen,'base_eur':str(base),
                                          'fx':str(fx),'fx_date':fx_data['date'],'observed_at':observed})
                matched+=1
            print(json.dumps({'set':set_id,'products':len(products),'matched':matched}),flush=True)
    report['rejected']=dict(rejected)
    report['applied']=retail.apply_updates(report['updates']) if args.apply and not report['errors'] else 0
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'candidates':len(rows),'matched':len(report['updates']),'applied':report['applied'],
                      'rejected':report['rejected'],'errors':report['errors']},ensure_ascii=False),flush=True)
    if report['errors']:raise SystemExit(1)


if __name__=='__main__':
    main()
