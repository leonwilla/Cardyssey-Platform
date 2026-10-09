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
r=load("resolve-cardtrader-ja-nm-prices")
class JapaneseMarketplaceTests(unittest.TestCase):
 def setUp(self):
  self.row=dict(card_id="official_ja_fixture",language_code="ja",identity_count=1,set_id="SV1V",local_id="001",
                official_count=78,rarity="C",german_species="Tannza",native_name="クヌギダマ")
  self.row.update(official_url="https://www.pokemon-card.com/card-search/details.php/card/1",official_rarity="rare_c_c",official_number="001/078",source_revision="test")
  self.names=[{"9":"Pineco","6":"Tannza","1":"クヌギダマ"},{"9":"Pikachu","6":"Pikachu","1":"ピカチュウ"}]
  self.e=dict(id=3215,code="sv1v",game_id=5,name="Violet ex")
  self.bp=dict(id=235578,name="Pineco",version="001/078",expansion_id=3215,game_id=5,category_id=73,
               fixed_properties=dict(collector_number="001",pokemon_rarity="Common"),
               editable_properties=[dict(name="pokemon_language",possible_values=["jp","jp"]),dict(name="pokemon_reverse"),dict(name="first_edition")])
  self.p=dict(id=1,blueprint_id=235578,name_en="Pineco",expansion=dict(id=3215),graded=False,on_vacation=False,
              quantity=1,description=None,price=dict(cents=20,currency="EUR"),price_cents=20,price_currency="EUR",
              properties_hash=dict(pokemon_language="jp",condition="Near Mint",signed=False,altered=False,
                                   first_edition=False,pokemon_reverse=False,collector_number="001",pokemon_rarity="Common"))
 def match(self,bps=None,products=None):
  return r.match(self.row,bps or [self.bp],products or {"235578":[self.p]},self.e,self.names)
 def test_exact_korean_near_mint_single(self):
  o,reason=self.match();self.assertIsNone(reason);self.assertEqual("0.2",o["amount"]);self.assertEqual("CARDTRADER_JP_NM",o["source"])
 def test_wrong_language_condition_and_blank_language_excluded(self):
  for key,value in [("pokemon_language","kr"),("pokemon_language",""),("condition","Slightly Played")]:
   self.setUp();self.p["properties_hash"][key]=value;self.assertIsNone(self.match()[0])
 def test_wrong_set_number_denominator_category_and_species(self):
  for key,value in [("category_id",66),("expansion_id",3216),("name","Pikachu"),("version","001/079")]:
   self.setUp();self.bp[key]=value;self.assertIsNone(self.match()[0])
  self.setUp();self.row["native_name"]="ピカチュウ";self.assertIsNone(self.match()[0])
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
  bad=copy.deepcopy(q);bad["properties_hash"]["pokemon_language"]="kr";bad.update(price=dict(cents=1,currency="EUR"),price_cents=1)
  o,_=self.match(products={"235578":[self.p,q,bad]})
  self.assertEqual(2,o["product_id"]);self.assertEqual("0.1",o["amount"]);self.assertEqual(2,o["qualifying_offers"])
 def test_high_single_ask_review(self):
  self.p.update(price=dict(cents=10001,currency="EUR"),price_cents=10001)
  self.assertEqual("high_asking_price_review",self.match()[1])
 def test_source_owned_prices_refresh_weekly(self):
  with patch.object(r.ko.retail,"db",return_value="[]") as db:r.load_targets(r.SOURCE)
  self.assertIn("p.source='CARDTRADER_JP_NM' AND (TRUE)",db.call_args_list[0].args[0])
 def test_korean_boosters_only(self):
  for code in ["SV1V","S12a","sv9a","SM11","sm9a"]:self.assertTrue(r.regular_set(code))
  for code in ["SV-P","BW-P","SCC","CS4a","base1"]:self.assertFalse(r.regular_set(code))
class OfficialPageTests(unittest.TestCase):
 def setUp(self):
  self.row=dict(native_name="クヌギダマ",image_source_url="https://www.pokemon-card.com/assets/card.jpg",set_id="SV1V",local_id="001")
  self.html='<h1 class="Heading1">クヌギダマ</h1><img class="fit" src="/assets/card.jpg"><div class="subtext Text-fjalla"><img class="img-regulation" alt="SV1V">&nbsp;001&nbsp;/&nbsp;078&nbsp;<img src="/assets/images/card/rarity/ic_rare_c_c.gif"></div>'
 def test_primary_printed_denominator_and_rarity(self):
  row,reason=r.official_page(self.row,self.html);self.assertIsNone(reason)
  self.assertEqual(78,row["official_count"]);self.assertEqual("C",row["rarity"])
 def test_wrong_native_title_image_set_and_number(self):
  for old,new in [("クヌギダマ","ピカチュウ"),("/assets/card.jpg","/assets/wrong.jpg"),('alt="SV1V"','alt="SV1S"'),("001&nbsp;","002&nbsp;")]:
   self.assertIsNone(r.official_page(self.row,self.html.replace(old,new))[0])
 def test_unknown_rarity_and_ambiguous_block_excluded(self):
  self.assertIsNone(r.official_page(self.row,self.html.replace("rare_c_c","rare_unknown"))[0])
  self.assertIsNone(r.official_page(self.row,self.html+self.html)[0])
 def test_japanese_import_rejects_korean_identity_and_foreign_source(self):
  with self.assertRaises(ValueError):r.apply_updates([dict(row=dict(card_id="official_ko_x",language_code="ko"),offer=dict(source=r.SOURCE))])
  with self.assertRaises(ValueError):r.apply_updates([],source="CARDTRADER_KO_NM")
 def test_atomic_loader_refresh_is_japanese_only(self):
  with patch.object(r.retail,"db",return_value="[]") as db:r.load_targets()
  self.assertIn("language_code='ja'",db.call_args_list[0].args[0])
  self.assertIn("card_id LIKE 'official_ja_%'",db.call_args_list[0].args[0])

class CachedOfficialRecordTests(unittest.TestCase):
 def setUp(self):
  import hashlib
  self.url="https://www.pokemon-card.com/card-search/details.php/card/1"
  self.row=dict(card_id="official_ja_"+hashlib.sha256(self.url.encode()).hexdigest()[:24],
    native_name="クヌギダマ",image_source_url="https://www.pokemon-card.com/assets/card.jpg",
    set_id="SV1V",local_id="001",rarity="rare_c_c",official_url=self.url,source_revision="test")
  self.raw=dict(url=self.url,jp_id=1,card_type="Pokémon",name="クヌギダマ",
    img=self.row["image_source_url"],set_name="SV1V",number="001",set_total="078",
    rarity="rare_c_c",rarity_img="https://www.pokemon-card.com/assets/images/card/rarity/ic_rare_c_c.gif")
 def test_pinned_cached_primary_record_supplies_printed_denominator(self):
  self.row["official_count"]=174
  result,reason=r.cached_official_record(self.row,self.raw,"test")
  self.assertIsNone(reason);self.assertEqual(78,result["official_count"]);self.assertEqual("C",result["rarity"])
 def test_wrong_source_revision_identity_image_name_number_and_rarity(self):
  self.assertIsNone(r.cached_official_record(self.row,self.raw,"other")[0])
  for key,value in [("url",self.url+"2"),("jp_id",2),("img","https://wrong/image"),("name","ピカチュウ"),
                    ("number","002"),("set_name","SV1S"),("card_type","Trainer"),("rarity","rare_r_c"),
                    ("set_total","0"),("rarity_img","https://wrong/icon")]:
   raw=dict(self.raw,**{key:value});self.assertIsNone(r.cached_official_record(self.row,raw,"test")[0])
 def test_xy_alias_requires_the_primary_product_title(self):
  self.row.update(set_id="XY11-Bb")
  self.raw.update(set_name="XY11-Bb",sources=[dict(name="拡張パック「爆熱の闘士」")])
  result,reason=r.cached_official_record(self.row,self.raw,"test")
  self.assertIsNone(reason);self.assertEqual("xy11f",result["market_code"])
  self.raw["sources"]=[dict(name="拡張パック「冷酷の反逆者」")]
  self.assertIsNone(r.cached_official_record(self.row,self.raw,"test")[0])

if __name__=="__main__":unittest.main()
