#!/usr/bin/env python3
"""Identity, currency and stale-write checks for additional Korean retailers."""
import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
def load(name):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+".py"))
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load("resolve-extra-ko-prices")
class ExtraKoreanTests(unittest.TestCase):
 def setUp(self):
  self.row=dict(card_id="official_ko_fixture",language_code="ko",identity_count=1,set_id="sv2a",local_id="174",official_count=165,
                rarity="AR",german_species="Nidoking",native_name="니드킹")
  self.names=[{"9":"Nidoking","6":"Nidoking","3":"니드킹"},{"9":"Pikachu","6":"Pikachu","3":"피카츄"}]
  v=dict(id=2,title="Near Mint",option1="Near Mint",option2=None,option3=None,sku="sku",available=True,price="10.99")
  self.p=dict(id=1,title="Nidoking 174/165 - 151 (Korean)",handle="nidoking",product_type="Single Card",
              tags=["Language: Korean","Pokémon","Single Card"],options=[dict(name="Condition")],variants=[v])
  self.d=copy.deepcopy(self.p);self.d.update(body_html="Nidoking 174/165, a Pokémon TCG single from the 151 Korean set.")
  self.d["variants"][0]["price_currency"]="USD"
  self.a=copy.deepcopy(self.p);self.a["url"]="/products/nidoking"
  self.a["variants"][0].update(price=1099,quantity_rule=dict(min=1,increment=1),quantity_price_breaks=[],selling_plan_allocations=[])
 def match(self,key="level",currency="USD"):
  return r.match_offer(self.row,self.p,self.d,self.a,self.names,key,currency)
 def test_exact_level_offer(self):
  o,e=self.match();self.assertIsNone(e);self.assertEqual("10.99",o["amount"]);self.assertEqual("USD",o["currency"])
 def test_wrong_language_duplicate_identity_or_denominator(self):
  for key,val in [("language_code","ja"),("identity_count",2),("official_count",166),("local_id","175")]:
   self.setUp();self.row[key]=val;self.assertIsNotNone(self.match()[1])
 def test_wrong_species_and_korean_name(self):
  self.row["native_name"]="피카츄";self.assertEqual("species",self.match()[1])
  self.setUp();self.p["title"]=self.p["title"].replace("Nidoking","Pikachu");self.assertEqual("species",self.match()[1])
 def test_special_prints_and_unknown_sets_excluded(self):
  for title in ["Nidoking 174/165 (Master Ball) - 151 (Korean)","Nidoking 174/165 - Unknown (Korean)",
                "Nidoking 174/166 - 151 (Korean)","PSA Nidoking 174/165 - 151 (Korean)"]:
   self.assertIsNone(r.identity(title,"level"))
 def test_unlabelled_rare_foil_excluded(self):
  self.row["rarity"]="R";self.assertEqual("ambiguous_rarity",self.match()[1])
 def test_condition_stock_and_product_identity_must_agree(self):
  self.d["variants"][0]["title"]="Lightly Played";self.assertEqual("condition",self.match()[1])
  self.setUp();self.a["variants"][0]["available"]=False;self.assertEqual("stock",self.match()[1])
  self.setUp();self.d["id"]=3;self.assertEqual("product_identity",self.match()[1])
 def test_currency_and_minor_units(self):
  self.assertEqual("currency",self.match(currency="CAD")[1])
  self.a["variants"][0]["price"]=True;self.assertEqual("price_currency",self.match()[1])
  self.setUp();self.d["variants"][0]["price_currency"]="GBP";self.assertEqual("price_currency",self.match()[1])
  self.setUp();self.d["variants"][0]["price"]="1099";self.assertEqual("price_currency",self.match()[1])
 def test_bundles_subscriptions_excluded(self):
  self.a["variants"][0]["quantity_rule"]["min"]=2;self.assertEqual("bundle",self.match()[1])
  self.setUp();self.a["variants"][0]["requires_selling_plan"]=True;self.assertEqual("bundle",self.match()[1])
 def test_explicit_korean_tag_and_option_required(self):
  self.p["tags"]=[];self.assertEqual("language",self.match()[1])
  self.setUp();self.d["options"][0]["name"]="Language";self.assertEqual("options",self.match()[1])
 def shiny(self):
  self.row.update(set_id="sv5a",local_id="024",official_count=66,rarity="U",german_species="Windewoge",native_name="굽이치는물결")
  self.names=[{"9":"Walking Wake","6":"Windewoge","3":"굽이치는물결"}]
  for p in (self.p,self.d,self.a):
   p["title"]="KOR Walking Wake 024/066 Crimson Haze Uncommon | Near Mint"
   p["options"]=[dict(name="Title")]
   p["variants"][0].update(title="Default Title",option1="Default Title",price="1.25")
  self.d["variants"][0]["price_currency"]="GBP";self.a["variants"][0]["price"]=125
  self.d["body_html"]="(sv5a) <ul><li><strong>Language:</strong> Korean</li><li><strong>Condition:</strong> Near Mint</li><li><strong>Reverse Holo:</strong> No</li><li><strong>Card Number:</strong> 024/066</li><li><strong>Finish:</strong> Non-Holo</li></ul>"
 def test_shiny_explicit_finish_and_gbp(self):
  self.shiny();o,e=self.match("shiny","GBP");self.assertIsNone(e);self.assertEqual("1.25",o["amount"])
 def test_shiny_reverse_finish_and_missing_condition_excluded(self):
  self.shiny();self.d["body_html"]=self.d["body_html"].replace("Non-Holo","Reverse Holo");self.assertEqual("printing",self.match("shiny","GBP")[1])
  self.shiny();self.d["body_html"]=self.d["body_html"].replace("Near Mint","Played");self.assertEqual("body_identity",self.match("shiny","GBP")[1])
 def test_owned_prices_refresh_every_week(self):
  for source in ("WEB_LEVELUP_KO","WEB_SHINY_KO"):
   with patch.object(r.ko.retail,"db",return_value="[]") as db:r.ko.load_targets(source)
   self.assertIn("p.source='"+source+"' AND (TRUE)",db.call_args.args[0])
if __name__=="__main__":
 if "--postgres" in sys.argv:
  fixtures=load("test-price-round3")
  for source in ("WEB_LEVELUP_KO","WEB_SHINY_KO"):fixtures.postgres_tests(source=source)
 else:unittest.main()
