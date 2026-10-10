#!/usr/bin/env python3
import copy,importlib.util,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
s=importlib.util.spec_from_file_location("prices",Path(__file__).with_name("resolve-pokewallet-ja-market-prices.py"));p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
class Tests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,10,17,tzinfo=timezone.utc)
  self.row=dict(set_id="SV1V",local_id="001",official_count=78,rarity="C",official_url="url",official_number="001/078",official_rarity="C",source_revision="rev")
  self.bp=dict(id=1,name="Pineco",tcg_player_id=568227)
  self.ps=dict(language="jap",set_id="23606",set_code="SV1V")
  self.record=dict(id="pk_123abc",card_info=dict(name="Pineco",set_code="SV1V",set_id="23606",card_number="001/078",rarity="Common",hp="60.0",product_type="card"),
   tcgplayer=dict(url="https://www.tcgplayer.com/product/568227",prices=[dict(sub_type_name="Normal",market_price=.17,updated_at="2026-10-10T10:00:00")]),
   images=dict(languages=["en"]))
 def offer(self):return p.market_offer(self.row,self.bp,self.record,self.ps,self.now)
 def test_exact_product_and_japanese_set_despite_english_image(self):
  offer,reason=self.offer();self.assertIsNone(reason);self.assertEqual(offer["language"],"ja");self.assertEqual(offer["basis"],"MARKET_ESTIMATE");self.assertIsNone(offer["in_stock"]);self.assertEqual(offer["condition"],"aggregate-market")
 def test_wrong_set_language_id_name_number_rarity_type_rejected(self):
  for key,value in [("name","Pikachu"),("set_code","SV1S"),("set_id","12"),("card_number","001/079"),("rarity","Uncommon"),("product_type","sealed"),("hp","0")]:
   self.setUp();self.record["card_info"][key]=value;self.assertIsNone(self.offer()[0])
  self.setUp();self.ps["language"]="eng";self.assertIsNone(self.offer()[0])
  self.setUp();self.record["tcgplayer"]["url"]="https://www.tcgplayer.com/product/12";self.assertIsNone(self.offer()[0])
 def test_finish_duplicate_missing_zero_and_old_quote_rejected(self):
  for key,value in [("sub_type_name","Holofoil"),("market_price",0),("market_price",None),("updated_at","2026-09-01T00:00:00"),("updated_at","2026-10-11T00:00:00")]:
   self.setUp();self.record["tcgplayer"]["prices"][0][key]=value;self.assertIsNone(self.offer()[0])
  self.setUp();self.record["tcgplayer"]["prices"]*=2;self.assertIsNone(self.offer()[0])
 def test_image_only_and_cardmarket_only_cannot_prove_product(self):
  self.record["tcgplayer"]=None;self.assertIsNone(self.offer()[0])
 def test_mega_codes_not_arbitrary_promo_sets(self):
  for code in ["m1L","M1S","M2a"]:self.assertTrue(p.ja.regular_set(code))
  for code in ["M-P","MEP","PROMO"]:self.assertFalse(p.ja.regular_set(code))
if __name__=="__main__":unittest.main()
