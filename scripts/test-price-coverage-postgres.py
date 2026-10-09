#!/usr/bin/env python3
"""Exercise production SQL against connection-local temporary tables, then roll back."""
import importlib.util
import json
import subprocess
from pathlib import Path


def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def sql_test(setup, query):
    sql="BEGIN; SET LOCAL statement_timeout='10s';\n"+setup+'\n'+query+'\nROLLBACK;'
    result=subprocess.run(['docker','exec','-i','cardyssey-db','psql','-U','cardyssey','-d','cardyssey',
                           '-X','-qAt','-v','ON_ERROR_STOP=1'],input=sql,text=True,
                          capture_output=True,check=True,timeout=20)
    return result.stdout.strip().splitlines()


def main():
    retail=load('resolve-zhtw-retailer-prices')
    finalize=load('finalize-unpriced-backlog')
    audit=load('audit-price-coverage')
    setup="""
    CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,source text,
      base_eur numeric,resolution_status text,failure_detail text,updated_at timestamptz,next_attempt_at timestamptz);
    CREATE TEMP TABLE tcg_price_history(card_id text,language_code text,variant_id text,source text,base_eur numeric,captured_at timestamptz);
    INSERT INTO tcg_price_cache VALUES
      ('ok','zh-tw','generated','OLD',NULL,'NO_PRICE',NULL,'2026-01-01Z',NULL),
      ('race','zh-tw','generated','NEW',99,'PRICE_FOUND',NULL,'2026-01-02Z',NULL);
    """
    observed=[]
    def test_db(sql):
        result=sql_test(setup,sql+"\nSELECT COUNT(*) FROM tcg_price_history; SELECT base_eur FROM tcg_price_cache WHERE card_id='race';")
        observed.extend(result)
        return result[0]
    retail.db=test_db
    updates=[]
    for card_id in ('ok','race'):
        updates.append(dict(row=dict(card_id=card_id,variant_id='generated',updated_at='2026-01-01Z',resolution_status='NO_PRICE'),
                            offer=dict(source='WEB_BEEHIVE_HK',hkd='2.00',title="Test's card",url='https://beehivetcg.com/products/test',product_id=1),
                            fx='0.11',fx_date='2026-10-08',observed_at='2026-10-09T08:00:00Z',base_eur='0.2391'))
    assert retail.apply_updates(updates)==1,observed
    assert observed==['1','1','99'],observed
    print('PASS: atomic cache/history update, quote escaping and concurrent-price protection')

    values=[]
    for i,reason in enumerate(finalize.LEGACY_REASONS):
        values.append("('legacy%d','de','g',NULL,NULL,'NO_PUBLIC_PRICE',%s,'2026-01-01Z',NULL)"%(i,retail.quote(reason)))
    values.append("('manual','ja','g',NULL,NULL,'NO_PUBLIC_PRICE','unreleased promo','2026-01-01Z',NULL)")
    values.append("('priced','de','g','NEW',10,'PRICE_FOUND',%s,'2026-01-01Z',NULL)"%retail.quote(finalize.LEGACY_REASONS[0]))
    values.append("('excluded','fr','g',NULL,NULL,'NO_PUBLIC_PRICE',%s,'2026-01-01Z',NULL)"%retail.quote(finalize.LEGACY_REASONS[0]))
    repair_setup=setup+'\nDELETE FROM tcg_price_cache; INSERT INTO tcg_price_cache VALUES '+','.join(values)+';'
    checks="""
    SELECT COUNT(*) FROM tcg_price_cache WHERE resolution_status='NO_PRICE' AND updated_at='2026-01-01Z' AND next_attempt_at>NOW();
    SELECT resolution_status FROM tcg_price_cache WHERE card_id='manual';
    SELECT resolution_status FROM tcg_price_cache WHERE card_id='priced';
    SELECT resolution_status FROM tcg_price_cache WHERE card_id='excluded';
    """
    result=sql_test(repair_setup,finalize.REPAIR_SQL+checks)
    assert result==['de|3','3','NO_PUBLIC_PRICE','PRICE_FOUND','NO_PUBLIC_PRICE'],result
    print('PASS: only blanket deferrals reopen; manual holds, successes and excluded languages survive')

    coverage_setup=setup+"""
    CREATE TEMP TABLE catalog_cards_mirror(language_code text,card_id text,set_id text,local_id text,variants jsonb,details_complete boolean);
    INSERT INTO catalog_cards_mirror VALUES
      ('ko','missing','SM1','001','[]',true),
      ('ko','twin','SM1','1','[{"id":"normal"}]',true),
      ('ko','uncovered','SM1','002','[]',true),
      ('ko','pocket','A1','003','[]',true),
      ('fr','ignored','SM1','003','[]',true);
    """
    result=json.loads(sql_test(coverage_setup,audit.SUMMARY_SQL)[0])
    ko=next(row for row in result if row['language_code']=='ko')
    assert len(result)==6 and ko['catalog_entries']==3,result
    assert ko['missing_variants']==2 and ko['missing_with_number_twin']==1 and ko['missing_without_number_twin']==1,ko
    assert ko['missing_cache']==1 and ko['price_found']==0,ko
    print('PASS: missing variants/cache visible; number twins separated; Pocket and other languages excluded')


if __name__=='__main__':
    main()
