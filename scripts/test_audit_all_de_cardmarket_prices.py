import importlib.util
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
spec=importlib.util.spec_from_file_location("audit_all_cm",Path(__file__).with_name("audit-all-de-cardmarket-prices.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AuditAllGermanPrices(unittest.TestCase):
    def base(self,**kwargs):
        row=dict(card_id="a",variant_id="one",product_ids=["77"],variant={"type":"Normal"},
                 variant_count=1,legacy_variant="NORMAL",source="TCGDEX",price=1)
        row.update(kwargs)
        return row
    def test_one_product_with_guide_staged_not_promoted(self):
        result=module.calculate([self.base()],{"77":{"trend":1.5}})
        self.assertEqual(result[0]["status"],"GUIDE_CANDIDATE_NOT_LANGUAGE_NM_VERIFIED")
        self.assertEqual(result[0]["guide_value_eur"],1.5)
        self.assertEqual(result[0]["prior_source"],"TCGDEX")
    def test_multicandidate_never_invent_price(self):
        item=module.calculate([self.base(product_ids=["77","88"])],
                              {"77":{"trend":1},"88":{"trend":2}})[0]
        self.assertEqual(item["status"],"MULTIPLE_PRODUCT_CANDIDATES")
        self.assertIsNone(item["guide_value_eur"])
    def test_special_print_not_same_as_regular(self):
        item=module.calculate([self.base(variant={"type":"Normal","stamps":["staff"]})],
                              {"77":{"trend":10}})[0]
        self.assertEqual(item["status"],"SPECIAL_PRINT_IDENTITY_UNVERIFIED")
    def test_reverse_holo_not_assumed_separate(self):
        item=module.calculate([self.base(variant={"type":"Reverse"},variant_count=3)],
                              {"77":{"trend-holo":5}})[0]
        self.assertEqual(item["status"],"HOLO_REVERSE_SPLIT_UNVERIFIED")
    def test_no_priceguide_does_not_override(self):
        item=module.calculate([self.base()],{})[0]
        self.assertEqual(item["status"],"PRODUCT_HAS_NO_GUIDE")
        self.assertIsNone(item["guide_value_eur"])

if __name__=="__main__":unittest.main()
