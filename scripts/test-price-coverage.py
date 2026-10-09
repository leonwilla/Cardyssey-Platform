#!/usr/bin/env python3
"""Regression tests for exact retail matching and truthful backlog classification."""
import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


retail = load('resolve-zhtw-retailer-prices')


class RetailMatchingTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(language_code='zh-tw',card_id='SC1a-001',variant_id='generated',
                        legacy_variant='NORMAL',set_id='SC1a',local_id='001',name='飛天螳螂',
                        official_count=154,variant_count=1,variant=dict(type='normal',stamps=[],size='standard'))
        self.product = dict(id=123,title='SC1a 001/154 飛天螳螂 C',handle='sc1a-001-card',tags=[],
                            variants=[dict(id=456,title='Default Title',available=True,price='2.00',sku='pkmcnsc1a-001')])

    def match(self):
        return retail.match_offer(self.row,self.product,'beehivetcg.com','SC1a')

    def test_exact_chinese_numbered_live_single(self):
        offer, reason = self.match()
        self.assertIsNone(reason)
        self.assertEqual(offer['hkd'],'2.00')
        self.assertEqual(offer['source'],'WEB_BEEHIVE_HK')

    def test_rejects_wrong_set_even_inside_right_collection(self):
        self.product['title']='SC1b 001/154 飛天螳螂 C'
        self.assertEqual(self.match()[1],'set')

    def test_rejects_wrong_denominator(self):
        self.product['title']='SC1a 001/155 飛天螳螂 C'
        self.assertEqual(self.match()[1],'number')

    def test_rejects_name_and_printing_suffixes(self):
        for name in ('飛天螳螂V','飛天螳螂 鏡面','飛天螳螂 damaged','飛天螳螂 PSA10'):
            with self.subTest(name=name):
                self.product['title']='SC1a 001/154 '+name
                self.assertEqual(self.match()[1],'name_or_printing')

    def test_rejects_foil_edition_multiple_and_unproven_catalog_variants(self):
        for key,value in [('foil','reverse'),('subtype','unlimited'),('stamps',['1st edition'])]:
            with self.subTest(key=key):
                self.row['variant'][key]=value
                self.assertEqual(self.match()[1],'catalog_variant')
                del self.row['variant'][key]
        self.row['variant_count']=2
        self.assertEqual(self.match()[1],'catalog_variant')

    def test_rejects_unverified_language(self):
        self.product['variants'][0]['sku']='pkmjpsc1a-001'
        self.assertEqual(self.match()[1],'language')

    def test_rejects_sold_out_reference(self):
        self.product['variants'][0]['available']=False
        self.assertEqual(self.match()[1],'sold_out')

    def test_legacy_sku_requires_chinese_category_and_exact_number(self):
        self.product['variants'][0]['sku']='SC1a-001'
        self.assertEqual(self.match()[1],'language')
        self.product['product_type']='PKMCN'
        self.assertIsNone(self.match()[1])
        self.product['variants'][0]['sku']='SC1a-002'
        self.assertEqual(self.match()[1],'language')

    def test_rejects_nonpositive_or_nonfinite_price(self):
        for value in ('0','-1','NaN','Infinity','invalid'):
            with self.subTest(value=value):
                self.product['variants'][0]['price']=value
                self.assertEqual(self.match()[1],'price')

    def test_rejects_condition_or_foil_options(self):
        self.product['variants'][0]['title']='Reverse Holo'
        self.assertEqual(self.match()[1],'retailer_variant')
        self.product['variants'][0]['title']='Default Title'
        self.product['variants'].append(copy.deepcopy(self.product['variants'][0]))
        self.assertEqual(self.match()[1],'retailer_variant')

    def test_whitespace_fullwidth_and_leading_zero_normalization(self):
        self.product['title']='SC1A　００１／１５４　飛天螳螂 C'
        self.assertIsNone(self.match()[1])

    def test_provider_failure_is_not_empty_success(self):
        with patch.object(retail,'get_json',side_effect=TimeoutError('timeout')):
            host,code,products,error=retail.load_collection(('beehivetcg.com','SC1a','test'))
        self.assertEqual(products,[])
        self.assertIn('TimeoutError',error)

    def test_incomplete_or_repeated_pagination_is_an_error(self):
        page={'products':[dict(id=i) for i in range(250)]}
        with patch.object(retail,'get_json',return_value=page):
            result=retail.load_collection(('beehivetcg.com','SC1a','test'))
        self.assertEqual(result[2],[])
        self.assertIn('pagination',result[3])

    def test_empty_apply_does_not_open_database(self):
        with patch.object(retail,'db') as db:
            self.assertEqual(retail.apply_updates([]),0)
            db.assert_not_called()


if __name__=='__main__':
    unittest.main()
