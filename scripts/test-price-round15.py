#!/usr/bin/env python3
import copy,importlib.util,json,unittest
from pathlib import Path
def load(name):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+".py"));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
black=load("resolve-blackrose-ko-prices");shop=load("resolve-shopify-ko-prices")
class BlackRoseTests(unittest.TestCase):
 def setUp(self):
  self.row=dict(card_id="official_ko_fixture",language_code="ko",identity_count=1,set_id="sv7",local_id="007",official_count=102,rarity="C",native_name="턱지충이",german_species="Mabula")
  self.names=[{"3":"턱지충이","6":"Mabula","9":"Grubbin"}]
  body="<p>Language: Korean</p><p>Condition: Near Mint</p><p>Set: sv7 (Scarlet &amp; Violet era)</p><p>Card Number: 007/102</p><p>Rarity: Common</p><p>Finish: Regular</p>"
  variant=dict(id=2,title="Default Title",option1="Default Title",option2=None,option3=None,sku="Grubbin",available=True,price="4.74")
  self.feed=dict(id=1,title="Grubbin 007/102 sv7 Korean Pokemon TCG Card NM Grass Basic Common",handle="grubbin",body_html=body,product_type="Collectible Trading Cards - Pokemon",options=[dict(name="Title")],variants=[variant])
  self.detail=copy.deepcopy(self.feed);self.detail["variants"][0]["price_currency"]="GBP"
  self.ajax=copy.deepcopy(self.feed);self.ajax.update(url="/products/grubbin",available=True,price_varies=False);self.ajax["variants"][0].update(price=474,quantity_rule=dict(min=1,increment=1))
 def offer(self):return black.match_offer(self.row,self.feed,self.detail,self.ajax,self.names,"GBP")
 def test_exact_single_asking_price(self):
  offer,reason=self.offer();self.assertIsNone(reason);self.assertEqual(offer["amount"],"4.74");self.assertEqual(offer["language"],"ko")
 def test_wrong_language_number_denominator_rarity_species(self):
  for key,value in [("language_code","ja"),("local_id","008"),("official_count",103),("rarity","U"),("native_name","피카츄"),("identity_count",2)]:
   self.setUp();self.row[key]=value;self.assertIsNone(self.offer()[0])
 def test_stock_price_currency_subscription_and_bundles(self):
  for key,value in [("available",False),("price",475),("title","Played"),("requires_selling_plan",True)]:
   self.setUp();self.ajax["variants"][0][key]=value;self.assertIsNone(self.offer()[0])
  self.setUp();self.ajax["variants"][0]["quantity_rule"]["min"]=2;self.assertIsNone(self.offer()[0])
  self.setUp();self.detail["variants"][0]["price_currency"]="USD";self.assertIsNone(self.offer()[0])
 def test_changed_body_and_reverse_or_graded_card_rejected(self):
  self.detail["body_html"]=self.detail["body_html"].replace("007/102","008/102");self.assertIsNone(self.offer()[0])
  for marker in ["Reverse Holo","PSA 10","Master Ball","Bundle"]:
   self.setUp();self.feed["title"]+=" "+marker;self.assertIsNone(self.offer()[0])
 def test_foil_rarity_cannot_use_regular_common_finish(self):
  self.row["rarity"]="R"
  for product in (self.feed,self.detail):product["body_html"]=product["body_html"].replace("Rarity: Common","Rarity: Rare")
  self.assertIsNone(self.offer()[0])
class StructuredProductTests(unittest.TestCase):
 def setUp(self):
  self.detail=dict(id=1,title="Pikachu",variants=[dict(id=2,title="Korean / Near Mint / Normal",sku="s10a073-2")])
  self.group=dict(**{"@type":"ProductGroup"},productGroupID="1",name="Pikachu",url="https://nerocards.de/products/pikachu",hasVariant=[dict(**{"@type":"Product"},name="Pikachu - Korean / Near Mint / Normal",sku="s10a073-2",offers=dict(url="https://nerocards.de/products/pikachu?variant=2",price="29.98",priceCurrency="EUR",availability="http://schema.org/InStock"))])
 def parse(self):return shop.structured_product('<script type="application/ld+json">'+json.dumps(self.group)+'</script>',self.detail)
 def test_group_variant_uses_child_sku_and_exact_live_variant(self):
  self.assertEqual(self.parse()["offers"][0]["sku"],"s10a073-2")
 def test_wrong_group_id_sku_variant_name_or_offer_url_rejected(self):
  for key,value in [("productGroupID","9"),("name","Wrong")]:
   self.setUp();self.group[key]=value
   with self.assertRaises(ValueError):self.parse()
  for key,value in [("sku","wrong"),("name","Pikachu - Japanese / Near Mint / Normal")]:
   self.setUp();self.group["hasVariant"][0][key]=value
   with self.assertRaises(ValueError):self.parse()
  self.setUp();self.group["hasVariant"][0]["offers"]["url"]="https://example.com/products/pikachu?variant=2"
  with self.assertRaises(ValueError):self.parse()
 def test_single_product_sku_can_normalize_single_offer(self):
  text='<script type="application/ld+json">'+json.dumps({"@type":"Product","sku":"exact","offers":{"url":"url"}})+'</script>'
  self.assertEqual(shop.structured_product(text)["offers"][0]["sku"],"exact")
 def test_multiple_products_are_held(self):
  text='<script type="application/ld+json">'+json.dumps({"@type":"Product"})+'</script>'
  with self.assertRaises(ValueError):shop.structured_product(text+text)
retail=load("resolve-zhtw-retailer-prices")
class MissingOnlyRetailTests(unittest.TestCase):
 def test_found_snapshot_cannot_refresh(self):
  with self.assertRaises(ValueError):retail.apply_updates([dict(row=dict(resolution_status="PRICE_FOUND"))],missing_only=True)
def postgres_tests():
 import subprocess
 from unittest.mock import patch
 setup="""CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,source text,base_eur numeric,updated_at timestamptz,resolution_status text,failure_detail text,next_attempt_at timestamptz);
 CREATE TEMP TABLE tcg_price_history(card_id text,language_code text,variant_id text,source text,base_eur numeric,captured_at timestamptz);"""
 update=dict(row=dict(card_id="fixture",language_code="zh-tw",variant_id="generated",updated_at="2026-10-10T12:00:00Z",resolution_status="NO_PRICE"),
 offer=dict(source="WEB_PLAYERSCLUB_ZHTW",currency="HKD",amount="10",title="fixture",url="https://example.com/fixture",product_id=1),base_eur="1",fx=".1",fx_date="2026-10-09",observed_at="2026-10-10T12:00:00Z")
 sqls=[]
 with patch.object(retail,"db",side_effect=lambda sql:sqls.append(sql) or "0"):retail.apply_updates([update],missing_only=True)
 for current,extra,expected in [(0,"",1),(5,"",0),(0,"INSERT INTO tcg_price_cache VALUES('fixture','zh-tw','other','trusted',5,NOW(),'NO_PRICE',NULL,NULL);",0)]:
  insert="INSERT INTO tcg_price_cache VALUES('fixture','zh-tw','generated','none',"+str(current)+",'2026-10-10T12:00:00Z','NO_PRICE',NULL,NULL);"
  result=subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-X","-qAt","-v","ON_ERROR_STOP=1"],input="BEGIN;"+setup+insert+extra+sqls[0]+"ROLLBACK;",text=True,capture_output=True,check=True,timeout=25)
  assert int(result.stdout.strip())==expected,result.stdout
 print("PASS: 3 PostgreSQL traditional-Chinese missing-only preservation cases")
if __name__=="__main__":
 import sys
 if "--postgres" in sys.argv:postgres_tests()
 else:unittest.main()
