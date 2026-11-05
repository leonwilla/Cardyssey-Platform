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
    def test_one_row_one_variant(self):
        rows=[{"cardyssey_karte":"a","variante_id":"1","set_id":"s","sonderdruck":"","foil":"","stempel":""},
              {"cardyssey_karte":"a","variante_id":"2","set_id":"s","sonderdruck":"","foil":"","stempel":""}]
        result=module.prioritize(rows,[])
        self.assertEqual(len(result),2)
        self.assertEqual({r["variante_id"] for r in result},{"1","2"})

if __name__=="__main__":unittest.main()
