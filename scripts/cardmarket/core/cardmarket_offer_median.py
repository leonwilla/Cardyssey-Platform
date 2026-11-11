#!/usr/bin/env python3
"""Offline median of authorized Cardmarket offer exports; never calls blocked pages.

Prices are ASKING prices, not sales. Missing condition is 'assumed NM' only for
explicit German offers; language/edition/finish are never guessed.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import statistics
try:
    from .market_condition_policy import classify_condition
except ImportError:  # script invocation
    from market_condition_policy import classify_condition

GOOD={'MT','NM'}
BAD={'EX','GD','LP','PL','PO'}

def evaluate(data):
    expected=data.get('expected') or {}
    if str(expected.get('language','')).lower() != 'de':
        raise ValueError('German-only rollout: expected.language must be de')
    if not str(expected.get('cardmarket_product_id','')).isdigit():
        raise ValueError('Verified numeric Cardmarket product id required')
    if expected.get('finish') not in ('normal','holo','reverse'):
        raise ValueError('Expected finish must be normal, holo or reverse')
    if expected.get('first_edition') not in (True,False):
        raise ValueError('Expected first_edition must be explicitly true or false')
    records=data.get('offers')
    if not isinstance(records,list):raise ValueError('offers must be an array')
    rejected=Counter(); accepted=[]; seen=set(); assumed=0
    for item in records:
        if not isinstance(item,dict):rejected['invalid_offer']+=1;continue
        oid=str(item.get('id') or '').strip()
        if not oid or oid in seen:rejected['missing_or_duplicate_offer_id']+=1;continue
        seen.add(oid)
        if str(item.get('product_id') or '')!=str(expected['cardmarket_product_id']):
            rejected['wrong_product']+=1;continue
        if str(item.get('language') or '').strip().lower() not in ('de','german','deutsch'):
            rejected['wrong_or_unknown_language']+=1;continue
        if item.get('finish') != expected['finish']:
            rejected['wrong_or_unknown_finish']+=1;continue
        if item.get('first_edition') is not expected['first_edition']:
            rejected['wrong_or_unknown_edition']+=1;continue
        if item.get('signed') is not False or item.get('altered') is not False or item.get('graded') is not False:
            rejected['signed_altered_graded_or_unverified']+=1;continue
        if item.get('bundle_size',1)!=1 or item.get('is_playset',False) is not False:
            rejected['bundle_or_playset']+=1;continue
        condition=str(item.get('condition') or '').strip().upper()
        state=('explicit_nm' if condition in GOOD else 'rejected' if condition in BAD else classify_condition(item.get('condition'),language='de'))
        if state not in ('explicit_nm','assumed_nm'):
            rejected['condition_not_nm']+=1;continue
        try:
            amount=Decimal(str(item['price_eur']))
            if not amount.is_finite() or amount<=0:raise InvalidOperation
        except (InvalidOperation,KeyError,TypeError,ValueError):
            rejected['invalid_price']+=1;continue
        accepted.append(amount)
        if state=='assumed_nm':assumed+=1
    pages=data.get('pagination') or {}
    # An offer sample is not complete unless source explicitly certifies all pages.
    complete=(pages.get('all_pages_fetched') is True and pages.get('capped') is False
        and isinstance(pages.get('total_offers'),int)
        and pages['total_offers'] == len(seen))
    result={'product_id':str(expected['cardmarket_product_id']), 'language':'de',
            'basis':'active_asking_offers_not_sales','accepted':len(accepted),
            'assumed_nm':assumed,'rejected':dict(rejected),
            'all_pages_complete':complete,'median_eur':None,'status':'NO_ELIGIBLE_OFFERS'}
    if accepted:
        med=statistics.median(accepted)
        result['median_eur']=str(med.quantize(Decimal('0.01')))
        result['status']='COMPLETE_ASKING_MEDIAN' if complete else 'PARTIAL_SAMPLE_MEDIAN_NOT_MARKET_WIDE'
    result['safe_to_auto_publish']=bool(accepted and complete and assumed==0)
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('json_file',type=Path)
    ap.add_argument('--report',type=Path)
    args=ap.parse_args()
    output=evaluate(json.loads(args.json_file.read_text(encoding='utf-8')))
    rendered=json.dumps(output,ensure_ascii=False,indent=2)+'\n'
    if args.report:args.report.write_text(rendered,encoding='utf-8')
    print(rendered,end='')
