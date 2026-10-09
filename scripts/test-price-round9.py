#!/usr/bin/env python3
"""Exact Korean CardTrader identity/listing and atomic-write regression checks."""
import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
def load(name):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+".py"));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load("resolve-cardtrader-ko-nm-prices")
class KoreanMarketplaceTests(unittest.TestCase):
 def setUp(self):
  self.row=dict(card_id="official_ko_fixture",language_code="ko",identity_count=1,set_id="SV1V",local_id="001",
                official_count=78,rarity="C",german_species="Tannza",native_name="피콘")
  self.names=[{"9":"Pineco","6":"Tannza","3":"피콘"},{"9":"Pikachu","6":"Pikachu","3":"피카츄"}]
  self.e=dict(id=3215,code="sv1v",game_id=5,name="Violet ex")
  self.bp=dict(id=235578,name="Pineco",version="001/078",expansion_id=3215,game_id=5,category_id=73,
               fixed_properties=dict(collector_number="001",pokemon_rarity="Common"),
               editable_properties=[dict(name="pokemon_language",possible_values=["jp","kr"]),dict(name="pokemon_reverse"),dict(name="first_edition")])
  self.p=dict(id=1,blueprint_id=235578,name_en="Pineco",expansion=dict(id=3215),graded=False,on_vacation=False,
              quantity=1,description=None,price=dict(cents=20,currency="EUR"),price_cents=20,price_currency="EUR",
              properties_hash=dict(pokemon_language="kr",condition="Near Mint",signed=False,altered=False,
                                   first_edition=False,pokemon_reverse=False,collector_number="001",pokemon_rarity="Common"))
 def match(self,bps=None,products=None):
  return r.match(self.row,bps or [self.bp],products or {"235578":[self.p]},self.e,self.names)
 def test_exact_korean_near_mint_single(self):
  o,reason=self.match();self.assertIsNone(reason);self.assertEqual("0.2",o["amount"]);self.assertEqual("CARDTRADER_KO_NM",o["source"])
 def test_wrong_language_condition_and_blank_language_excluded(self):
  for key,value in [("pokemon_language","jp"),("pokemon_language",""),("condition","Slightly Played")]:
   self.setUp();self.p["properties_hash"][key]=value;self.assertIsNone(self.match()[0])
 def test_wrong_set_number_denominator_category_and_species(self):
  for key,value in [("category_id",66),("expansion_id",3216),("name","Pikachu"),("version","001/079")]:
   self.setUp();self.bp[key]=value;self.assertIsNone(self.match()[0])
  self.setUp();self.row["native_name"]="피카츄";self.assertIsNone(self.match()[0])
 def test_reverse_signed_altered_first_edition_and_grading_excluded(self):
  for key in ["pokemon_reverse","first_edition","signed","altered"]:
   self.setUp();self.p["properties_hash"][key]=True;self.assertIsNone(self.match()[0])
  self.setUp();self.p["graded"]=True;self.assertIsNone(self.match()[0])
  self.setUp();del self.p["properties_hash"]["pokemon_reverse"];self.assertIsNone(self.match()[0])
 def test_printing_ambiguity_and_special_blueprints_excluded(self):
  self.assertEqual("blueprint_missing_or_ambiguous",self.match(bps=[self.bp,copy.deepcopy(self.bp)])[1])
  for version in ["Master Ball | 001/078","Reverse Holo | 001/078","Promo | 001/078"]:
   self.setUp();self.bp["version"]=version;self.assertIsNone(self.match()[0])
 def test_official_identity_must_be_unique_and_rarity_match(self):
  self.row["identity_count"]=2;self.assertIsNone(self.match()[0])
  self.setUp();self.row["rarity"]="R";self.assertIsNone(self.match()[0])
  self.setUp();self.row["rarity"]="U";self.assertIsNone(self.match()[0])
 def test_ordinary_rare_requires_explicit_holo_and_nonreverse_offer(self):
  self.row["rarity"]="R";self.bp["fixed_properties"]["pokemon_rarity"]="Holo Rare"
  self.bp["version"]="Holo Rare | 001/078";self.p["properties_hash"]["pokemon_rarity"]="Holo Rare"
  self.assertIsNotNone(self.match()[0])
  self.p["properties_hash"]["pokemon_reverse"]=True;self.assertIsNone(self.match()[0])
  self.p["properties_hash"]["pokemon_reverse"]=False
  for version in ["Rare | 001/078","Non-Holo Rare | 001/078","Holo Rare Reverse | 001/078","001/078"]:
   self.bp["version"]=version;self.assertIsNone(self.match()[0])
  self.bp["version"]="Holo Rare | 001/078";self.bp["fixed_properties"]["pokemon_rarity"]="Rare"
  self.assertIsNone(self.match()[0])
 def test_shiny_requires_explicit_compatible_rarity(self):
  self.row["rarity"]="S";self.bp["fixed_properties"]["pokemon_rarity"]="Shiny Holo Rare"
  self.bp["version"]="Shiny Holo Rare | 001/078";self.p["properties_hash"]["pokemon_rarity"]="Shiny Holo Rare"
  self.assertIsNotNone(self.match()[0])
  self.bp["fixed_properties"]["pokemon_rarity"]="Holo Rare"
  self.assertIsNone(self.match()[0])
 def test_quantity_bundle_description_and_vacation(self):
  for key,value in [("quantity",2),("quantity",True),("bundle_size",2),("bundled_quantity",2),
                    ("description","Selling a lot"),("on_vacation",True)]:
   self.setUp();self.p[key]=value;self.assertIsNone(self.match()[0])
 def test_minor_units_currency_and_positive_values(self):
  for key,value in [("cents",True),("cents",0),("cents",20.0),("currency","USD")]:
   self.setUp();self.p["price"][key]=value;self.assertIsNone(self.match()[0])
  self.setUp();self.p["price_cents"]=21;self.assertIsNone(self.match()[0])
 def test_listing_number_and_identity_must_agree_with_blueprint(self):
  self.p["properties_hash"]["collector_number"]="002";self.assertIsNone(self.match()[0])
  self.setUp();self.p["name_en"]="Pikachu";self.assertIsNone(self.match()[0])
  self.setUp();self.p["properties_hash"]["pokemon_rarity"]="Uncommon";self.assertIsNone(self.match()[0])
 def test_lowest_qualifying_offer_retains_exact_product_proof(self):
  q=copy.deepcopy(self.p);q.update(id=2,price=dict(cents=10,currency="EUR"),price_cents=10)
  bad=copy.deepcopy(q);bad["properties_hash"]["pokemon_language"]="jp";bad.update(price=dict(cents=1,currency="EUR"),price_cents=1)
  o,_=self.match(products={"235578":[self.p,q,bad]})
  self.assertEqual(2,o["product_id"]);self.assertEqual("0.1",o["amount"]);self.assertEqual(2,o["qualifying_offers"])
 def test_high_single_ask_review(self):
  self.p.update(price=dict(cents=10001,currency="EUR"),price_cents=10001)
  self.assertEqual("high_asking_price_review",self.match()[1])
 def test_source_owned_prices_refresh_weekly(self):
  with patch.object(r.ko.retail,"db",return_value="[]") as db:r.ko.load_targets(r.SOURCE)
  self.assertIn("p.source='CARDTRADER_KO_NM' AND (TRUE)",db.call_args.args[0])
 def test_korean_boosters_only(self):
  for code in ["SV1V","S12a","sv9a","SM11","sm9a","XY8b","M1S"]:self.assertTrue(r.regular_set(code))
  for code in ["SV-P","BW-P","SCC","CS4a","base1"]:self.assertFalse(r.regular_set(code))
if __name__=="__main__":
 if "--postgres" in sys.argv:load("test-price-round3").postgres_tests(source=r.SOURCE)
 else:unittest.main()
