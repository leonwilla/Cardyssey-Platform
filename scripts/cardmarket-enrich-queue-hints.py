#!/usr/bin/env python3
"""Conservative catalog search hints from verified-set singleton candidates.
Never treats a catalog candidate as an authenticated product-page proof.
"""
import argparse,csv,hashlib,json,os
from pathlib import Path
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
FEEDS=Path('/home/tv/.local/state/cardyssey-queue/price-feeds')
URL='https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json'
ROOT=Path('/home/tv/cardshop')
def enrich(language,base=BASE,root=ROOT,feeds=FEEDS):
    if language not in ('de','en'):raise ValueError('language')
    data=json.loads((feeds/(hashlib.sha256(URL.encode()).hexdigest()+'.json')).read_text())
    product={str(x['idProduct']):x for x in data['products']}
    valid={}
    with (root/f'reports/cardmarket-identity-worklist-{language}.csv').open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['classification'] not in ('ONE_PRODUCT_IN_VERIFIED_SET','ONE_PRODUCT_IN_VERIFIED_SET_SPECIAL_PRINT'):
                continue
            pid=row['matched_set_ids'].strip()
            if not pid.isdigit() or ',' in pid:continue
            if pid not in product:continue
            valid[(row['card_id'],row['variant_id'])]=(pid,product[pid]['name'])
    queue=base/f'queue-{language}.csv'
    with queue.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f);fields=list(reader.fieldnames or []);rows=list(reader)
    if not rows:raise RuntimeError('empty queue')
    for col in ('catalog_singleton_id','catalog_search_name'):
        if col not in fields:fields.append(col)
    audit_path=root/'reports/cardmarket-set-mapping-risk-audit.json'
    audit=json.loads(audit_path.read_text(encoding='utf-8')) if audit_path.exists() else {}
    quarantined={x['setId'] for x in audit.get('cases',[]) if x.get('status')=='AMBIGUOUS_OVERLAPPING_EXPANSIONS' and not (x.get('independentlyConfirmedOverride') or x.get('variantIdConsensusMatch'))}
    count=0;held=0
    for r in rows:
        if r.get('set_id') in quarantined and r.get('routing_state')!='VERIFIED_PRODUCT_ID':
            r['cardmarket_ids']=''
            r['candidate_status']='SET_EXPANSION_AMBIGUOUS'
            r['catalog_singleton_id']='';r['catalog_search_name']=''
            held+=1
            continue
        pair=valid.get((r['cardyssey_karte'],r['variante_id']))
        r['catalog_singleton_id'],r['catalog_search_name']=pair if pair else ('','')
        if pair:count+=1
    tmp=queue.with_suffix('.csv.enrich.tmp')
    with tmp.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    os.replace(tmp,queue)
    return {'language':language,'rows':len(rows),'verified_set_singleton_hints':count,'quarantined_ambiguous_set_variants':held}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--language',choices=('de','en'),required=True);a=p.parse_args()
    print(json.dumps(enrich(a.language),ensure_ascii=False))
