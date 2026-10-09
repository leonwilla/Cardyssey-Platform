#!/usr/bin/env python3
import copy
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path


def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


cardland=load('resolve-cardland-zhtw-prices')


class CardLandTests(unittest.TestCase):
    def setUp(self):
        self.row=dict(language_code='zh-tw',card_id='SDL-003',variant_id='generated',legacy_variant='NORMAL',
                      set_id='SDL',local_id='003',official_count=21,name='九尾',variant_count=1,
                      variant=dict(type='normal',size='standard'))
        self.product=dict(id=28108,name='九尾',sku='HK-SDL-003/021-noth-28108',
                          type='simple',has_options=False,variations=[],is_in_stock=True,
                          is_purchasable=True,is_on_backorder=False,
                          categories=[dict(id=4999,name='寶可夢繁中版卡 單卡專區')],
                          prices=dict(price='5',currency_code='HKD',currency_minor_unit=0),
                          permalink='https://cardland.com.hk/product/test/')

    def match(self):return cardland.match_offer(self.row,self.product)

    def test_exact_in_stock_single(self):
        offer,reason=self.match();self.assertIsNone(reason);self.assertEqual(offer['hkd'],'5')

    def test_minor_currency_units(self):
        self.product['prices'].update(price='500',currency_minor_unit=2)
        self.assertEqual(self.match()[0]['hkd'],'5')

    def test_rejects_wrong_printing(self):
        self.product['sku']='HK-SDL-003/021-hoth-28108'
        self.assertEqual(self.match()[1],'sku_or_printing')

    def test_rejects_wrong_set_number_and_name(self):
        for key,value,reason in [('sku','HK-SDM-003/021-noth-28108','set'),
                                 ('sku','HK-SDL-004/021-noth-28108','number'),
                                 ('sku','HK-SDL-003/022-noth-28108','number'),
                                 ('name','九尾V','name')]:
            with self.subTest(value=value):
                original=self.product[key];self.product[key]=value
                self.assertEqual(self.match()[1],reason);self.product[key]=original

    def test_rejects_wrong_language_category(self):
        self.product['categories']=[dict(id=1,name='Pokemon Japanese')]
        self.assertEqual(self.match()[1],'language')

    def test_stock_and_backorder(self):
        for key,value in [('is_in_stock',False),('is_purchasable',False),('is_on_backorder',True)]:
            with self.subTest(key=key):
                original=self.product[key];self.product[key]=value
                self.assertEqual(self.match()[1],'stock');self.product[key]=original

    def test_rejects_foreign_currency_and_invalid_units(self):
        self.product['prices']['currency_code']='TWD'
        self.assertEqual(self.match()[1],'currency')
        self.product['prices']['currency_code']='HKD'
        for units in (True,None,8):
            self.product['prices']['currency_minor_unit']=units
            self.assertEqual(self.match()[1],'price_units')

    def test_rejects_free_or_malformed_price(self):
        for value,reason in [('0','price'),('NaN','price_units'),('-5','price_units'),('5.00','price_units')]:
            self.product['prices']['price']=value;self.assertEqual(self.match()[1],reason)

    def test_rejects_unverified_options(self):
        self.product['has_options']=True;self.assertEqual(self.match()[1],'retailer_variant')

    def test_rejects_foreign_link_and_wrong_id(self):
        self.product['permalink']='https://example.com/product/test/'
        self.assertEqual(self.match()[1],'product_identity')
        self.product['permalink']='https://cardland.com.hk/product/test/'
        self.product['id']=123;self.assertEqual(self.match()[1],'product_identity')


def postgres_tests():
    repair=load('repair-verified-catalog-twins')
    setup="""
    CREATE TEMP TABLE catalog_cards_mirror(card_id text,language_code text,set_id text,local_id text,
      image_source_url text,raw_payload jsonb,variants jsonb,details_complete boolean);
    CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,legacy_variant text,
      source text,base_eur numeric,updated_at timestamptz,resolution_status text,failure_detail text,next_attempt_at timestamptz,
      UNIQUE(card_id,language_code,variant_id));
    CREATE TEMP TABLE tcg_price_history(card_id text,language_code text,variant_id text,source text,base_eur numeric,captured_at timestamptz);
    INSERT INTO catalog_cards_mirror VALUES
      ('source','ja','S1','1','https://official/image','{"name":"九 尾"}','[{"id":"normal","legacyVariant":"NORMAL"}]',true),
      ('duplicate','ja','S1','001','https://official/image','{"name":"九尾"}','[]',true),
      ('wrong-image','ja','S1','1','https://official/other','{"name":"九尾"}','[]',true),
      ('wrong-name','ja','S1','1','https://official/image','{"name":"九尾V"}','[]',true),
      ('wrong-language','ko','S1','1','https://official/image','{"name":"九尾"}','[]',true);
    INSERT INTO tcg_price_cache VALUES('source','ja','normal','NORMAL','TCGDEX',10,NOW()-INTERVAL '2 days','PRICE_FOUND',NULL,NOW()+INTERVAL '5 days');
    INSERT INTO tcg_price_history VALUES('source','ja','normal','TCGDEX',10,NOW()-INTERVAL '2 days');
    """
    checks="""
    SELECT COUNT(*) FROM catalog_cards_mirror WHERE jsonb_array_length(variants)>0;
    SELECT COUNT(*) FROM tcg_price_cache WHERE card_id='duplicate' AND updated_at=NOW()-INTERVAL '2 days';
    SELECT COUNT(*) FROM tcg_price_history WHERE card_id='duplicate' AND captured_at=NOW()-INTERVAL '2 days';
    """
    def run(extra=''):
        sql="BEGIN; SET LOCAL statement_timeout='10s';\n"+setup+extra+'\n'+repair.APPLY_SQL+'\n'+repair.APPLY_SQL+'\n'+checks+'\nROLLBACK;'
        result=subprocess.run(['docker','exec','-i','cardyssey-db','psql','-U','cardyssey','-d','cardyssey',
                               '-X','-qAt','-v','ON_ERROR_STOP=1'],input=sql,text=True,capture_output=True,check=True,timeout=20)
        lines=result.stdout.strip().splitlines()
        return json.loads(lines[0]),json.loads(lines[1]),lines[2:]
    first,second,counts=run()
    assert first==dict(catalog_entries_repaired=1,price_rows_copied=1,original_history_points_copied=1),first
    assert second==dict(catalog_entries_repaired=0,price_rows_copied=0,original_history_points_copied=0),second
    assert counts==['2','1','1'],counts
    print('PASS: exact duplicate repair, rejection of partial identities, retained timestamps and repeat-run idempotence')
    extra="""INSERT INTO catalog_cards_mirror SELECT 'ambiguous-source',language_code,set_id,local_id,image_source_url,raw_payload,variants,details_complete FROM catalog_cards_mirror WHERE card_id='source';"""
    first,second,counts=run(extra)
    assert first['catalog_entries_repaired']==0 and first['price_rows_copied']==0,first
    assert counts==['2','0','0'],counts
    print('PASS: ambiguous canonical identities are rejected')


if __name__=='__main__':
    import sys
    if '--postgres' in sys.argv:postgres_tests()
    else:unittest.main()
