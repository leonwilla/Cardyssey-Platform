#!/usr/bin/env python3
"""Missing-only recovery must preserve positive prices, including other variants."""
import copy,importlib.util,json,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
def load(name):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+".py"));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ko=load("resolve-cardtrader-ko-nm-prices");ja=load("resolve-cardtrader-ja-nm-prices")
class RecoveryTests(unittest.TestCase):
 def test_filter_positive_prices_and_found_status_before_network(self):
  rows=[dict(card_id="positive",old_status="NO_PRICE"),dict(card_id="found",old_status="PRICE_FOUND"),dict(card_id="new",old_status=None)]
  with patch.object(ko.ko.retail,"db",return_value='["positive"]'):
   self.assertEqual(["new"],[r["card_id"] for r in ko.missing.filter_targets(rows,ko.ko.retail)])
 def test_independent_species_longest_unique_and_all_languages(self):
  names=[{"1":"コイル","6":"Magnetilo","9":"Magnemite"},{"1":"ジバコイル","6":"Magnezone","9":"Magnezone"}]
  self.assertEqual("Magnezone",ja.independent_species("ジバコイル ex",names)["6"])
  self.assertIsNone(ja.independent_species("ジバコイル",names+[names[1]]))
  self.assertIsNone(ja.independent_species("ジバコイル",[{"1":"ジバコイル","6":"Magnezone"}]))
 def test_writer_rejects_refresh_snapshot(self):
  for module,writer in [(ko,ko.ko.apply_updates),(ja,ja.apply_updates)]:
   with self.assertRaises(ValueError):
    writer([dict(row=dict(language_code="ja" if module is ja else "ko",card_id="official_ja_test" if module is ja else "official_ko_test",old_status="PRICE_FOUND"),offer=dict(source=module.SOURCE))],module.SOURCE,missing_only=True)
unicorn=load("resolve-unicorn-ko-prices")
class UnicornTests(unittest.TestCase):
 def setUp(self):
  self.row=dict(card_id="official_ko_fixture",language_code="ko",identity_count=1,set_id="SV1V",local_id="086",official_count=78,rarity="AR",native_name="슬리프",german_species="Traumato")
  self.names=[{"3":"슬리프","6":"Traumato","9":"Drowzee"}]
  self.product=dict(id=1,handle="drowzee",title="Drowzee 086/078 - Korean Art Rare Holo - SV1V: Violet ex - Near Mint",product_type="Raw Single",
    tags=["Korean","Near Mint","Art Rare","Holo","086/078","SV1V"],variants=[dict(id=2,product_id=1,title="Near Mint",sku="TU-S-216",available=True,price="23.99")])
  self.ajax=dict(id=1,handle="drowzee",title=self.product["title"],available=True,price_varies=False,requires_selling_plan=False,
    variants=[dict(id=2,title="Near Mint",sku="TU-S-216",available=True,price=2399)])
  self.detail=copy.deepcopy(self.product);self.detail["tags"]=", ".join(self.detail["tags"])
  self.detail["variants"][0].update(price_currency="USD",quantity_rule=dict(min=1,increment=1));self.detail["variants"][0].pop("available")
 def match(self):return unicorn.match_offer(self.row,self.product,self.ajax,self.names)
 def test_exact_nm_korean_single_and_public_detail_currency(self):
  self.assertEqual("23.99",self.match()[0]["amount"]);self.assertTrue(unicorn.detail_agrees(self.product,self.detail))
 def test_other_language_number_denominator_rarity_and_species_held(self):
  for k,v in [("language_code","ja"),("local_id","085"),("official_count",79),("rarity","SR"),("native_name","피카츄"),("identity_count",2)]:
   self.setUp();self.row[k]=v;self.assertIsNone(self.match()[0])
 def test_stock_condition_price_and_subscription_held(self):
  for k,v in [("available",False),("price",2400),("title","Lightly Played")]:
   self.setUp();self.ajax["variants"][0][k]=v;self.assertIsNone(self.match()[0])
  self.setUp();self.ajax["requires_selling_plan"]=True;self.assertIsNone(self.match()[0])
 def test_tags_and_multiple_options_cannot_prove_identity(self):
  self.product["tags"].remove("Korean");self.assertIsNone(self.match()[0])
  self.setUp();self.product["variants"].append(copy.deepcopy(self.product["variants"][0]));self.assertIsNone(self.match()[0])
 def test_single_product_endpoint_must_agree_on_currency_price_and_sku(self):
  for k,v in [("price_currency","EUR"),("price","24"),("sku","wrong")]:
   self.setUp();self.detail["variants"][0][k]=v;self.assertFalse(unicorn.detail_agrees(self.product,self.detail))

market=load("resolve-tcgcsv-ja-market-prices")
class JapaneseMarketTests(unittest.TestCase):
 def setUp(self):
  self.row=dict(local_id="001",official_count=78,rarity="C",official_url="url",official_number="001/078",official_rarity="C",source_revision="rev")
  self.bp=dict(id=235578,name="Pineco",tcg_player_id=568227,fixed_properties=dict(pokemon_rarity="Common"))
  self.product=dict(productId=568227,name="Pineco",categoryId=85,groupId=23606,presaleInfo=dict(isPresale=False),
    url="https://www.tcgplayer.com/product/568227/pokemon-japan-sv1v-violet-ex-pineco",
    extendedData=[dict(name="Number",value="001/078"),dict(name="Rarity",value="Common"),dict(name="HP",value="60")])
  self.quotes=[dict(productId=568227,subTypeName="Normal",marketPrice=.2)]
 def offer(self):return market.market_offer(self.row,self.bp,self.product,self.quotes,23606)
 def test_exact_japanese_market_estimate_without_claiming_stock_or_nm(self):
  offer,reason=self.offer();self.assertIsNone(reason);self.assertEqual("MARKET_ESTIMATE",offer["basis"]);self.assertIsNone(offer["in_stock"]);self.assertEqual("aggregate-market",offer["condition"])
 def test_english_category_wrong_tcg_id_number_name_rarity_and_presale_rejected(self):
  for k,v in [("categoryId",3),("productId",12),("name","Pikachu"),("groupId",1),("presaleInfo",dict(isPresale=True))]:
   self.setUp();self.product[k]=v;self.assertIsNone(self.offer()[0])
  for field,value in [("Number","001/079"),("Rarity","Rare"),("HP","")]:
   self.setUp();next(x for x in self.product["extendedData"] if x["name"]==field)["value"]=value;self.assertIsNone(self.offer()[0])
 def test_wrong_finish_missing_zero_and_duplicate_market_price_rejected(self):
  for k,v in [("subTypeName","Holofoil"),("marketPrice",None),("marketPrice",0)]:
   self.setUp();self.quotes[0][k]=v;self.assertIsNone(self.offer()[0])
  self.setUp();self.quotes.append(dict(self.quotes[0]));self.assertIsNone(self.offer()[0])
 def test_exact_number_suffix_allowed_and_wrong_number_suffix_rejected(self):
  self.product["name"]="Pineco - 001/078";self.assertIsNotNone(self.offer()[0])
  self.product["name"]="Pineco - 002/078";self.assertIsNone(self.offer()[0])
 def test_foil_price_requires_foil_finish(self):
  self.row["rarity"]="AR";self.bp["fixed_properties"]["pokemon_rarity"]="Illustration Rare"
  next(x for x in self.product["extendedData"] if x["name"]=="Rarity")["value"]="Illustration Rare"
  self.assertIsNone(self.offer()[0]);self.quotes[0]["subTypeName"]="Holofoil";self.assertIsNotNone(self.offer()[0])

def postgres_tests():
 setup="""CREATE TEMP TABLE catalog_cards_mirror(card_id text,language_code text,set_id text,local_id text,raw_payload jsonb,image_source_url text,variants jsonb);
 CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,legacy_variant text,source text,base_eur numeric,updated_at timestamptz,resolution_status text,failure_detail text,next_attempt_at timestamptz,UNIQUE(card_id,language_code,variant_id));
 CREATE TEMP TABLE tcg_price_history(card_id text,language_code text,variant_id text,source text,base_eur numeric,captured_at timestamptz);"""
 count=0
 for lang,module,writer,source in [("ko",ko,ko.ko.apply_updates,ko.SOURCE),("ja",ja,ja.apply_updates,ja.SOURCE),("ja",ja,ja.apply_updates,"POKEWALLET_JP_MARKET"),("ko",ko,ko.ko.apply_updates,"WEB_NERO_KO"),("ko",ko,ko.ko.apply_updates,"WEB_CARDANVIL_KO"),("ko",ko,ko.ko.apply_updates,"WEB_BLACKROSE_KO")]:
  cid="official_"+lang+"_fixture"
  row=dict(card_id=cid,language_code=lang,set_id="SV1V",local_id="001",native_name="name",image_source_url="image",old_variants=[],old_updated=None,old_status=None)
  update=dict(row=row,offer=dict(source=source),base_eur="1",observed_at="2026-10-10T12:00:00Z")
  sqls=[]
  with patch.object(ko.ko.retail if lang=="ko" else ja.retail,"db",side_effect=lambda sql:sqls.append(sql) or '{"variants":0,"prices":0,"history":0}'):
   writer([update],source,missing_only=True)
  insert="INSERT INTO catalog_cards_mirror VALUES("+",".join(map(module.ko.retail.quote,[cid,lang,"SV1V","001",'{"name":"name"}',"image","[]"]))+");"
  for label,extra,expected in [
    ("missing","",dict(variants=1,prices=1,history=1)),
    ("other_variant_positive","INSERT INTO tcg_price_cache(card_id,language_code,variant_id,base_eur,resolution_status) VALUES('"+cid+"','"+lang+"','other',5,'PRICE_FOUND');",dict(variants=0,prices=0,history=0)),
    ("inconsistent_positive","INSERT INTO tcg_price_cache(card_id,language_code,variant_id,base_eur,resolution_status) VALUES('"+cid+"','"+lang+"','other',5,'NO_PRICE');",dict(variants=0,prices=0,history=0))]:
   command=["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-X","-qAt","-v","ON_ERROR_STOP=1"]
   result=subprocess.run(command,input="BEGIN; SET LOCAL statement_timeout='15s';"+setup+insert+extra+sqls[0]+"ROLLBACK;",text=True,capture_output=True,check=True,timeout=25)
   actual=json.loads(result.stdout.strip());assert actual==expected,(lang,label,actual)
   count+=1
 print("PASS: "+str(count)+" PostgreSQL missing-only imports and positive-price preservation cases")
if __name__=="__main__":
 import sys
 if "--postgres" in sys.argv:postgres_tests()
 else:unittest.main()
