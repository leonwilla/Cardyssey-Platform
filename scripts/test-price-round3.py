#!/usr/bin/env python3
import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

ko=load('resolve-uturi-ko-prices')
ja=load('resolve-hareruya-ja-prices')

class MatchTests(unittest.TestCase):
    def setUp(self):
        self.row=dict(card_id='official_ko_test',language_code='ko',set_id='SV9',local_id='101',rarity='AR',
                      identity_count=1,german_species='Maracamba',native_name='마라카치',image_source_url='https://official/image',
                      old_variants=[],old_updated=None,old_status=None)
        self.url=ko.HOST+'/en/products/test'
        self.product=dict(title='Maractus 101 SV9',vendor='Pokémon',productType="Carte à l'unité",
            id='gid://shopify/Product/1',tags=['Rareté:AR','NomEN:Maractus'],setCodeCustom={'value':'SV9'},
            langueCustom={'value':'Coréen'},adjacentVariants=[],
            options=[{'name':'Title','optionValues':[{'name':'Default Title'}]}],
            selectedOrFirstAvailableVariant=dict(id='gid://shopify/ProductVariant/1',sku='101 SV9',title='Default Title',
                availableForSale=True,selectedOptions=[{'name':'Title','value':'Default Title'}],price={'amount':'1.4','currencyCode':'EUR'}))
        self.ld=dict(url=self.url,itemCondition='https://schema.org/NewCondition',offers=dict(url=self.url,
            availability='https://schema.org/InStock',price='1.4',priceCurrency='EUR'))
        self.names=[{'9':'Maractus','6':'Maracamba','3':'마라카치'}]

    def match(self):return ko.match_offer(self.row,self.product,self.ld,self.url,self.names)

    def test_exact_korean_identity(self):
        offer,reason=self.match();self.assertIsNone(reason);self.assertEqual(offer['currency'],'EUR')

    def test_wrong_set_number_language_and_species(self):
        for key,value,reason in [('identity_count',2,'catalog_identity'),('language_code','ja','catalog_identity'),
                                 ('local_id','102','set_number'),('rarity','SAR','rarity'),
                                 ('german_species','Pikachu','species'),('native_name','피카츄','species')]:
            with self.subTest(key=key):
                old=self.row[key];self.row[key]=value;self.assertEqual(self.match()[1],reason);self.row[key]=old
        self.product['langueCustom']['value']='Japanese';self.assertEqual(self.match()[1],'language')

    def test_rejects_grades_printing_and_options(self):
        self.product['title']='Maractus PSA 10 101 SV9';self.assertEqual(self.match()[1],'printing')
        self.product['title']='Maractus 101 SV9';self.product['options'][0]['optionValues'].append({'name':'Reverse'})
        self.assertEqual(self.match()[1],'variant')

    def test_stock_condition_currency_and_price_agree(self):
        variant=self.product['selectedOrFirstAvailableVariant']
        variant['availableForSale']=False;self.assertEqual(self.match()[1],'stock');variant['availableForSale']=True
        self.ld['itemCondition']='https://schema.org/UsedCondition';self.assertEqual(self.match()[1],'condition')
        self.ld['itemCondition']='https://schema.org/NewCondition'
        variant['price']['currencyCode']='JPY';self.assertEqual(self.match()[1],'currency')
        variant['price']['currencyCode']='EUR';self.ld['offers']['price']='140';self.assertEqual(self.match()[1],'price')

    def test_hydration_json_only_and_invalid_references(self):
        nodes=[{'_1':2},'loaderData',{'_3':4},'product',{'_5':6},'title','Test']
        html='streamController.enqueue('+json.dumps(json.dumps(nodes)+'\n')+')'
        self.assertEqual(ko.hydration.loader_data(html),{'product':{'title':'Test'}})
        nodes[4]={'_5':1000};html='streamController.enqueue('+json.dumps(json.dumps(nodes)+'\n')+')'
        with self.assertRaises(ValueError):ko.hydration.loader_data(html)

    def test_japanese_mixed_editions_are_rejected(self):
        variant=dict(id='unlimited',type='normal',size='standard',stamps=[],subtype='unlimited',legacyVariant='NORMAL')
        row=dict(language_code='ja',set_id='PCG9',local_id='018',official_count=68,legacy_variant='NORMAL',variant=variant,
                 all_variants=[variant],native_name='チルット',name='チルット')
        product=dict(id=1,handle='test',title='チルット:再販(C){水}〈018/068〉[P9]',body_html='名前：チルット<br>状態表記の無いカードは状態Aとなります。',
                     variants=[dict(id=2,title='Default Title',available=True,price='500')])
        self.assertIsNone(ja.match_offer(row,product)[1])
        product['title']='チルット(C){水}〈018/068〉[P9]';self.assertEqual(ja.match_offer(row,product)[1],'unmarked_edition')
        product['title']='チルット:1ED(C){水}〈018/068〉[P9]';self.assertEqual(ja.match_offer(row,product)[1],'edition')
        product['title']='【状態D】チルット:再販(C){水}〈018/068〉[P9]';self.assertEqual(ja.match_offer(row,product)[1],'title_or_condition')

    def test_high_japanese_single_asks_require_review(self):
        self.assertFalse(ja.needs_price_review({'amount':'10000'},ja.Decimal('0.006')))
        self.assertTrue(ja.needs_price_review({'amount':'250000'},ja.Decimal('0.006')))

    def test_blueprint_species_cannot_override_edition(self):
        variant=dict(id='unlimited',type='normal',size='standard',stamps=[],subtype='unlimited',legacyVariant='NORMAL')
        row=dict(language_code='ja',set_id='PCG9',local_id='018',official_count=68,legacy_variant='NORMAL',variant=variant,
                 all_variants=[variant],native_name='Wrong translated name',name='Wrong',blueprint_name='Swablu delta species',blueprint_id=123)
        product=dict(id=1,handle='test',title='チルット:再販(C){水}〈018/068〉[P9]',body_html='英語名：Swablu<br>状態表記の無いカードは状態Aとなります。',
                     variants=[dict(id=2,title='Default Title',available=True,price='500')])
        offer,reason=ja.match_offer(row,product);self.assertIsNone(reason)
        self.assertEqual(offer['identity_method'],'exact-edition-blueprint-species')
        row['blueprint_name']='Pikachu';self.assertEqual(ja.match_offer(row,product)[1],'name')
        row['blueprint_name']='Swablu';product['title']='チルット:1ED(C){水}〈018/068〉[P9]'
        self.assertEqual(ja.match_offer(row,product)[1],'edition')


class JapanesePromoTests(unittest.TestCase):
    def setUp(self):
        variant=dict(id='normal',type='normal',size='standard',stamps=[],subtype=None,foil=None,legacyVariant='NORMAL')
        self.row=dict(language_code='ja',set_id='SV-P',local_id='223',official_count=0,legacy_variant='NORMAL',
                      variant=variant,all_variants=[variant],native_name='トレーナーズポスト',name='トレーナーズポスト')
        self.product=dict(id=1,handle='9750606938432',title='トレーナーズポスト(PROMO){グッズ}〈223/SV-P〉[SV-P]',
                          body_html='状態表記の無いカードは状態Aとなります。',
                          variants=[dict(id=2,title='Default Title',available=True,price='850')])

    def test_exact_numbered_trainer_promo_without_species_metadata(self):
        offer,reason=ja.match_offer(self.row,self.product)
        self.assertIsNone(reason)
        self.assertEqual(offer['identity_method'],'exact-numbered-promo-native-title')

    def test_wrong_number_language_set_and_name_are_rejected(self):
        for title in ['トレーナーズポスト(PROMO){グッズ}〈135/SV-P〉[SV-P]',
                      'トレーナーズポスト(PROMO){グッズ}〈223/M-P〉[SV-P]',
                      'トレーナーズポスト(PROMO){グッズ}〈223/SV-P〉[M-P]',
                      'ダブルドラゴンエネルギー(PROMO){グッズ}〈223/SV-P〉[SV-P]',
                      'トレーナーズポスト:スタンプ(PROMO){グッズ}〈223/SV-P〉[SV-P]']:
            with self.subTest(title=title):
                self.product['title']=title
                self.assertIsNotNone(ja.match_offer(self.row,self.product)[1])
        self.setUp();self.row['language_code']='ko'
        self.assertEqual(ja.match_offer(self.row,self.product)[1],'set_language')

    def test_promo_special_printings_and_multiple_variants_are_rejected(self):
        for key,value in [('stamps',['event']),('foil','masterball'),('subtype','unlimited'),('type','reverse'),('size','jumbo')]:
            with self.subTest(key=key):
                self.setUp();self.row['variant'][key]=value
                self.assertEqual(ja.match_offer(self.row,self.product)[1],'promo_variant')
        self.setUp();self.row['all_variants'].append(dict(self.row['variant'],id='alternate'))
        self.assertEqual(ja.match_offer(self.row,self.product)[1],'promo_variant')

    def test_promo_condition_stock_and_options_are_rejected(self):
        self.product['variants'][0]['available']=False
        self.assertEqual(ja.match_offer(self.row,self.product)[1],'stock')
        self.setUp();self.product['body_html']='unknown condition'
        self.assertEqual(ja.match_offer(self.row,self.product)[1],'condition')
        self.setUp();self.product['variants'].append(dict(self.product['variants'][0],id=3))
        self.assertEqual(ja.match_offer(self.row,self.product)[1],'retailer_variant')

    def test_modern_denominator_cannot_override_classic_edition(self):
        self.row['set_id']='E1';self.row['official_count']=128
        self.product['title']='トレーナーズポスト(C){グッズ}〈223/SV-P〉[e1]'
        self.assertEqual(ja.match_offer(self.row,self.product)[1],'number')
        self.product['title']='トレーナーズポスト(C){グッズ}〈223/128〉[e1]'
        self.assertEqual(ja.match_offer(self.row,self.product)[1],'unmarked_edition')

def postgres_tests(source=ko.SOURCE):
    def db(sql):
        r=subprocess.run(['docker','exec','-i','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-X','-qAt','-v','ON_ERROR_STOP=1'],
            input="BEGIN; SET LOCAL statement_timeout='15s';\n"+sql+'\nROLLBACK;',text=True,capture_output=True,check=False,timeout=25)
        if r.returncode:raise RuntimeError(r.stderr)
        return r.stdout.strip().splitlines()
    setup="""
    CREATE TEMP TABLE catalog_cards_mirror (LIKE public.catalog_cards_mirror INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);
    CREATE TEMP TABLE catalog_sets_mirror (LIKE public.catalog_sets_mirror INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);
    CREATE TEMP TABLE catalog_supplemental_cards (LIKE public.catalog_supplemental_cards INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);
    CREATE TEMP TABLE catalog_set_code_aliases (LIKE public.catalog_set_code_aliases INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);
    CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,legacy_variant text,source text,base_eur numeric,updated_at timestamptz,resolution_status text,failure_detail text,next_attempt_at timestamptz,UNIQUE(card_id,language_code,variant_id));
    CREATE TEMP TABLE tcg_price_history(card_id text,language_code text,variant_id text,source text,base_eur numeric,captured_at timestamptz);
    """
    case=MatchTests();case.setUp();update=dict(row=case.row,offer=case.match()[0],base_eur='1.5217',observed_at='2026-10-09T12:00:00Z')
    update['offer']['source']=source
    captured=[]
    with patch.object(ko.retail,'db',lambda sql:captured.append(sql) or '{"variants":0,"prices":0,"history":0}'):
        ko.apply_updates([update],source=source)
    writer=captured[0]
    insert="""INSERT INTO catalog_cards_mirror(language_code,card_id,set_id,local_id,name,image_source_url,variants,raw_payload,details_complete)
        VALUES('ko','official_ko_test','SV9','101','마라카치','https://official/image','[]','{"name":"마라카치"}',TRUE);
    """
    result=db(setup+insert+writer+writer)
    assert json.loads(result[0])==dict(variants=1,prices=1,history=1),result
    assert json.loads(result[1])==dict(variants=0,prices=0,history=0),result
    concurrent="INSERT INTO tcg_price_cache VALUES('official_ko_test','ko','generated','NORMAL','OTHER',5,NOW(),'PRICE_FOUND',NULL,NULL);"
    result=db(setup+insert+concurrent+writer)
    assert json.loads(result[0])==dict(variants=0,prices=0,history=0),result
    print('PASS: atomic KO catalogue/cache/history import, repeat-run idempotence, concurrent newer prices preserved')

    details=dict(id='official_ko_test',languageCode='ko',setId='SV9',localId='101',name='마라카치',
        imageBase='https://official/image',setName='Test',officialCount=100,rarity='AR',variants=[])
    payload=dict(sourceId='official_ko_test',details=details,allowMatch=False,sourceUrl='https://official/source',revision='test',germanSpecies='Maracamba')
    imported=Path('scripts/catalog-supplemental-import.sql').read_text()
    def rows(p):return "CREATE TEMP TABLE source_rows(payload jsonb) ON COMMIT DROP; INSERT INTO source_rows VALUES("+ko.retail.quote(json.dumps(p))+"::jsonb);"
    # Run the actual supplement importer twice, using separate temporary staging tables.
    drop='DROP TABLE source_rows,resolved_rows,invalidated_price_prints;'
    check="SELECT jsonb_build_object('variants',jsonb_array_length(variants),'proof',raw_payload->>'_cardyssey_retail_variant_source') FROM catalog_cards_mirror;"
    first=rows(payload)+imported+writer+drop
    changed=copy.deepcopy(payload);changed['details']['imageBase']='https://official/corrected-image'
    result=db(setup+first+rows(payload)+imported+check+drop+rows(changed)+imported+check+
              "SELECT resolution_status || ':' || COALESCE(base_eur::text,'NULL') FROM tcg_price_cache;")
    assert json.loads(result[1])==dict(variants=1,proof=source),result
    assert json.loads(result[2])==dict(variants=0,proof=None),result
    assert result[3]=='NO_PRICE:NULL',result
    print('PASS: unchanged official imports preserve provenance; changed images clear derived variants/prices')

    # The generalized retail writer must match both card ID AND language.
    captured=[];ja_update=dict(row=dict(card_id='same',language_code='ja',variant_id='normal',updated_at='2026-10-08T00:00:00Z',resolution_status='NO_PRICE'),
        offer=dict(source='WEB_HARERUYA_JP',currency='JPY',amount='500',title="Offer's title",url='https://www.hareruya2.com/products/test',product_id=1),
        base_eur='3',fx='0.006',fx_date='2026-10-09',observed_at='2026-10-09T12:00:00Z')
    with patch.object(ja.retail,'db',lambda sql:captured.append(sql) or '0'):ja.retail.apply_updates([ja_update])
    result=db(setup+"INSERT INTO tcg_price_cache VALUES('same','ja','normal','NORMAL','OLD',NULL,'2026-10-08','NO_PRICE',NULL,NULL),('same','zh-tw','normal','NORMAL','OLD',NULL,'2026-10-08','NO_PRICE',NULL,NULL);"+captured[0]+"SELECT language_code || ':' || resolution_status FROM tcg_price_cache ORDER BY language_code;")
    assert result==['1','ja:PRICE_FOUND','zh-tw:NO_PRICE'],result
    print('PASS: JPY update retains provenance and cannot update a same-ID Chinese price')

    twins=load('repair-verified-catalog-twins')
    variant=json.dumps([dict(id='normal',type='normal',legacyVariant='NORMAL')])
    twin_rows="INSERT INTO catalog_cards_mirror(language_code,card_id,set_id,local_id,name,image_source_url,variants,raw_payload,details_complete) VALUES "
    for card,image in [('canonical','https://same/image'),('derived','https://same/image'),('wrong-image','https://different/image')]:
        twin_rows+="('ja',"+ko.retail.quote(card)+",'TEST','001','Name',"+ko.retail.quote(image)+","+ko.retail.quote(variant)+",'{\"name\":\"Name\"}',TRUE),"
    twin_rows=twin_rows.rstrip(',')+';'
    proof="INSERT INTO tcg_price_cache VALUES('derived','ja','normal','NORMAL','OLD',1,NOW(),'PRICE_FOUND','Exact catalogue duplicate of canonical; exact proof',NULL),('wrong-image','ja','normal','NORMAL','OLD',1,NOW(),'PRICE_FOUND','Exact catalogue duplicate of canonical; exact proof',NULL);"
    result=db(setup+twin_rows+proof+twins.APPLY_SQL+twins.APPLY_SQL+"SELECT card_id FROM catalog_cards_mirror WHERE raw_payload->>'_cardyssey_verified_variant_source'='canonical';")
    assert json.loads(result[0])['catalog_entries_repaired']==1,result
    assert json.loads(result[1])['catalog_entries_repaired']==0,result
    assert result[2:]==['derived'],result
    print('PASS: lost twin provenance restored only with exact identity and saved source evidence; no reciprocal alias or changed-image recovery')


if __name__=='__main__':
    if '--postgres' in sys.argv:postgres_tests()
    else:unittest.main()
