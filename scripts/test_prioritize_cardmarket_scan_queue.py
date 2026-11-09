import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("cm_priority",Path(__file__).with_name("prioritize-cardmarket-scan-queue.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class PriorityTests(unittest.TestCase):
    def test_missing_price_precedes_high_value(self):
        rows=[
          {"cardyssey_karte":"a","variante_id":"1","set_id":"one","prioritaet":"P2","sonderdruck":"","foil":"","stempel":""},
          {"cardyssey_karte":"b","variante_id":"2","set_id":"two","prioritaet":"P4","sonderdruck":"","foil":"","stempel":""},
          {"cardyssey_karte":"c","variante_id":"3","set_id":"three","prioritaet":"P2","sonderdruck":"Staff","foil":"","stempel":""}
        ]
        cache=[
          {"card_id":"a","variant_id":"1","status":"PRICE_FOUND","price":100,"source":"TCGCSV_TCGPLAYER"},
          {"card_id":"b","variant_id":"2","status":"NO_PRICE","price":0,"source":None},
          {"card_id":"c","variant_id":"3","status":"PRICE_FOUND","price":1,"source":"TCGDEX"}
        ]
        ordered=module.prioritize(rows,cache)
        self.assertEqual([x["cardyssey_karte"] for x in ordered],["b","a","c"])
        self.assertEqual([x["scan_tier"] for x in ordered],[0,1,2])
        self.assertEqual(ordered[0]["needs_price"],"YES")
    def test_priced_bulk_uses_price_feeds_not_browser(self):
        row={"cardyssey_karte":"bulk","variante_id":"v","set_id":"x",
             "sonderdruck":"","foil":"","stempel":""}
        cache=[{"card_id":"bulk","variant_id":"v","status":"PRICE_FOUND",
                "price":0.05,"source":"TCGDEX","rarity":"Häufig"}]
        self.assertEqual(module.prioritize([row],cache)[0]["scan_tier"],4)
    def test_empty_json_stamps_do_not_make_bulk_special(self):
        row={"cardyssey_karte":"bulk","variante_id":"v","set_id":"x",
             "sonderdruck":"","foil":"","stempel":"[]"}
        cache=[{"card_id":"bulk","variant_id":"v","status":"PRICE_FOUND",
                "price":0.05,"source":"TCGDEX","rarity":"Ungewöhnlich"}]
        out=module.prioritize([row],cache)[0]
        self.assertEqual(out["scan_tier"],4)
        self.assertEqual(out["needs_price"],"NO")
    def test_missing_bulk_stays_feed_only(self):
        row={"cardyssey_karte":"bulk","variante_id":"v","set_id":"x", "sonderdruck":"","foil":"","stempel":"[]"}
        cache=[{"card_id":"bulk","variant_id":"v","status":"NO_PRICE", "price":0, "rarity":"Häufig"}]
        out=module.prioritize([row],cache)[0]
        self.assertEqual(out['scan_tier'],4)
        self.assertEqual(out['needs_price'],'YES')

    def test_one_row_one_variant(self):
        rows=[{"cardyssey_karte":"a","variante_id":"1","set_id":"s","sonderdruck":"","foil":"","stempel":""},
              {"cardyssey_karte":"a","variante_id":"2","set_id":"s","sonderdruck":"","foil":"","stempel":""}]
        result=module.prioritize(rows,[])
        self.assertEqual(len(result),2)
        self.assertEqual({r["variante_id"] for r in result},{"1","2"})

if __name__=="__main__":unittest.main()
