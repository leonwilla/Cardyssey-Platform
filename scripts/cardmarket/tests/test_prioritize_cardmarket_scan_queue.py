import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("cm_priority",source_path("prioritize-cardmarket-scan-queue.py"))
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
        self.assertEqual([x["scan_tier"] for x in ordered],[0,1,4])
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
    def test_missing_bulk_is_eligible(self):
        row={"cardyssey_karte":"bulk","variante_id":"v","set_id":"x", "sonderdruck":"","foil":"","stempel":"[]"}
        cache=[{"card_id":"bulk","variant_id":"v","status":"NO_PRICE", "price":0, "rarity":"Häufig"}]
        out=module.prioritize([row],cache)[0]
        self.assertEqual(out['scan_tier'],0)
        self.assertEqual(out['needs_price'],'YES')

    def test_price_boundary_preserves_cents_and_precision(self):
        for amount, tier in [("1.50",4), ("1.99",4), ("1.99995",4), ("2.00",1), ("2.01",1), ("15.00",1)]:
            with self.subTest(amount=amount):
                row={"cardyssey_karte":"a","variante_id":"1","drucktyp":"normal"}
                cached={"card_id":"a","variant_id":"1","status":"PRICE_FOUND","price":amount}
                item=module.prioritize([row],[cached])[0]
                self.assertEqual((item["scan_tier"],item["existing_price_eur"]),(tier,amount))

    def test_confirmed_special_and_manual_eligibility(self):
        priced={"needs_price":"NO","existing_price_eur":"1.5","drucktyp":"normal"}
        cases=[
            ({"sonderdruck":"Staff","routing_state":"VERIFIED_PRODUCT_ID"},False,2),
            ({"stempel":'["Staff"]',"routing_state":"HUMAN_CONFIRMED"},False,2),
            ({"foil":"cosmos","routing_state":"SOURCE_ONLY"},True,2),
            ({"foil":"cosmos","routing_state":"SOURCE_ONLY"},False,4),
            ({"drucktyp":"reverse","routing_state":"VERIFIED_PRODUCT_ID"},True,4),
            ({"drucktyp":"holo","stempel":"[]"},False,4),
            ({"manual_scan_requested_at":"2026-11-18T09:00:00Z"},False,3),
        ]
        for attributes, human_confirmed, expected in cases:
            with self.subTest(attributes=attributes,human_confirmed=human_confirmed):
                self.assertEqual(module.browser_scan_tier({**priced,**attributes},human_confirmed),expected)

    def test_one_row_one_variant(self):
        rows=[{"cardyssey_karte":"a","variante_id":"1","set_id":"s","sonderdruck":"","foil":"","stempel":""},
              {"cardyssey_karte":"a","variante_id":"2","set_id":"s","sonderdruck":"","foil":"","stempel":""}]
        result=module.prioritize(rows,[])
        self.assertEqual(len(result),2)
        self.assertEqual({r["variante_id"] for r in result},{"1","2"})

if __name__=="__main__":unittest.main()
