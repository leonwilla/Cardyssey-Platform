#!/usr/bin/env python3
import importlib.util,json,unittest
from pathlib import Path
path=Path(__file__).with_name("cardmarket-median-all-offers.py")
spec=importlib.util.spec_from_file_location("cm_all_median",path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def sample():
    def offer(i,price,quantity=1):
        return {"offer_id":str(i),"product_id":"895610","language":"de","condition":"NM",
            "finish":"cosmos","edition":"other","signed":False,"altered":False,
            "graded":False,"bundle":False,"quantity":quantity,"price_eur":price}
    return {"expected":{"product_id":"895610","language":"de","finish":"cosmos","edition":"other"},
        "offers":[offer(1,"0,05",1),offer(2,"0,20",1),offer(3,"0,49",5),
                  offer(4,"0,99",1),offer(5,"1,50",1)],
        "pagination":{"all_pages_fetched":True,"total_offers":5,"capped":False},
        "print_identity_independently_verified":True}
class MedianTests(unittest.TestCase):
 def test_all_offers_not_five_cheapest(self):
    data=sample()
    self.assertEqual(m.evaluate(data)["median_all_offers_eur"],"0.49")
    self.assertEqual(m.evaluate(data)["median_quantity_weighted_eur"],"0.49")
 def test_one_listing_not_weighted_by_stock(self):
    d=sample();d["offers"][2]["quantity"]=200000
    self.assertEqual(m.evaluate(d)["median_all_offers_eur"],"0.49")
 def test_incomplete_pages_not_published(self):
    d=sample();d["pagination"]["all_pages_fetched"]=False
    x=m.evaluate(d)
    self.assertFalse(x["can_publish_print_price"])
    self.assertEqual(x["status"],"PARTIAL_ASKING_MEDIAN")
 def test_language_mismatch_rejected(self):
    d=sample();d["offers"][0]["language"]="en"
    x=m.evaluate(d)
    self.assertEqual(x["accepted_offers"],4)
    self.assertFalse(x["can_publish_print_price"])
 def test_reverse_mismatch_rejected(self):
    d=sample();d["offers"][1]["finish"]="reverse"
    self.assertFalse(m.evaluate(d)["can_publish_print_price"])
 def test_missing_print_confirmation(self):
    d=sample();d["print_identity_independently_verified"]=False
    self.assertFalse(m.evaluate(d)["can_publish_print_price"])
 def test_missing_quantity_does_not_count(self):
    d=sample();d["offers"][1].pop("quantity")
    self.assertEqual(m.evaluate(d)["accepted_offers"],4)
 def test_german_thousands(self):
    self.assertEqual(m.money("1.234,56 €"),m.money("1,234.56 €"))
if __name__=="__main__":unittest.main()
