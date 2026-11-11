#!/usr/bin/env python3
"""Promote COMPLETE filtered asking medians only for a human-confirmed print.

The browser samples are NOT sold prices. Unverified catalog mappings or
incomplete pagination never write a card price.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse,json,math,subprocess
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlsplit,parse_qs

def collect(path,language,now=None):
    if language not in ('de','en'):raise ValueError('language')
    now=now or datetime.now(timezone.utc)
    latest={}
    with path.open(encoding='utf-8-sig') as f:
        for line in f:
            try:
                x=json.loads(line)
                if x.get('card_id') and x.get('variant_id'):
                    latest[(x['card_id'],x['variant_id'])]=x
            except (ValueError,TypeError):continue
    results=[]
    for (card,variant),x in latest.items():
        if (x.get('language')!=language or x.get('identity_confirmed') is not True or
            x.get('status')!='COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED' or x.get('all_pages_complete') is not True):
            continue
        median=x.get('median_all_offers_eur')
        if isinstance(median,bool) or not isinstance(median,(float,int)) or not math.isfinite(median) or not 0<median<1e6:continue
        if not isinstance(x.get('verified_lang_nm_offers'),int) or x['verified_lang_nm_offers']<1:continue
        url=str(x.get('url') or '')
        u=urlsplit(url)
        if u.scheme!='https' or u.netloc!='www.cardmarket.com' or not u.path.startswith('/'+language+'/Pokemon/Products/Singles/'):
            continue
        q=parse_qs(u.query)
        if q.get('language')!=(['3'] if language=='de' else ['1']) or q.get('minCondition')!=['2']:
            continue
        # Only publish if edition/foil filters are explicit, not broad mixed offers.
        reverse=x.get('expected_reverse_holo')
        first=x.get('expected_first_edition')
        if reverse not in ('Y','N') or first not in ('Y','N'):continue
        # Do not import a mixed print's median under the guise of an exact
        # copyright, textured foil, promo stamp, or other unsupported print.
        if x.get('non_filterable_print_attributes') or x.get('exact_print_filter_supported') is False:continue
        if q.get('isReverseHolo')!=[reverse] or q.get('isFirstEd')!=[first]:continue
        try:seen=datetime.fromisoformat(str(x.get('seen_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
        except (ValueError,TypeError):continue
        if seen<now-timedelta(days=8) or seen>now+timedelta(hours=1):continue
        pid=str(x.get('product_id') or '')
        if not pid.isdecimal():continue
        results.append({'language':language,'card':card,'variant':variant,
            'product_id':pid,'url':url.split('?')[0],'price':round(median,4),'observed_at':seen.isoformat()})
    return results

SQL="""
WITH rows AS (
 SELECT item->>'language' AS lang,item->>'card' AS card,item->>'variant' AS variant,
 item->>'product_id' AS pid,item->>'url' AS url,(item->>'price')::numeric AS price,
 (item->>'observed_at')::timestamptz AS observed
 FROM jsonb_array_elements({payload}::jsonb) item
), approved AS (
 SELECT r.* FROM rows r JOIN price_source_routing p
 ON p.language_code=r.lang AND p.card_id=r.card AND p.variant_id=r.variant
 WHERE p.primary_provider='CARDMARKET' AND p.verification_state='VERIFIED_PRODUCT_ID'
 AND p.provider_product_id=r.pid
 AND (p.provider_product_url IS NULL OR p.provider_product_url='' OR split_part(p.provider_product_url,'?',1)=r.url)
 AND p.source_evidence LIKE 'Human confirmed exact%'
)
INSERT INTO tcg_price_cache(card_id,language_code,variant_id,source,base_eur,updated_at,resolution_status)
SELECT card,lang,variant,
 CASE WHEN lang='de' THEN 'CARDMARKET_DE_NM_WEB' ELSE 'CARDMARKET_EN_NM_WEB' END,
 price,observed,'PRICE_FOUND' FROM approved
ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET
 source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,
 updated_at=EXCLUDED.updated_at,resolution_status='PRICE_FOUND',failure_detail=NULL
WHERE tcg_price_cache.updated_at<=EXCLUDED.updated_at;
"""

def apply(rows):
    for i in range(0,len(rows),100):
        data=json.dumps(rows[i:i+100],ensure_ascii=False,separators=(',',':')).replace("'","''")
        sql='BEGIN;\n'+SQL.format(payload="'"+data+"'")+'\nCOMMIT;'
        subprocess.run(['docker','exec','-i','cardyssey-db','psql','-X','-q','-v','ON_ERROR_STOP=1',
                        '-U','cardyssey','-d','cardyssey'],input=sql,text=True,check=True,stdout=subprocess.DEVNULL)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--language',choices=('de','en'),required=True)
    p.add_argument('--results',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    rows=collect(a.results,a.language)
    if a.apply and rows:apply(rows)
    print(json.dumps({'language':a.language,'full_filtered_candidates':len(rows),
       'applied_with_human_print_verification_only':a.apply,'basis':'complete_active_asking_median_not_sold'}))
