import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("cm_import",Path(__file__).with_name("import-cardmarket-browser-observations.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ImportTests(unittest.TestCase):
    queue=[{"cardyssey_karte":"mep-095","variante_id":"legacy:holo","cardmarket_ids":"895610"}]
    good={"card_id":"mep-095","variant_id":"legacy:holo","product_id":"895610",
          "status":"FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE",
          "de_nm_offers":50,"sample_median_eur":0.15}
    def test_good_sample_is_staged_only(self):
        rows=module.select_observations([self.good],self.queue)
        self.assertEqual(len(rows),1)
        self.assertTrue(rows[0]["candidate"]["no_verified_print_identity"])
        self.assertIn("price_review_cases",module.sql_for(rows))
        self.assertNotIn("tcg_price_cache",module.sql_for(rows))
    def test_wrong_product_never_staged(self):
        self.assertEqual(module.select_observations([{**self.good,"product_id":"999"}],self.queue),[])
    def test_bad_price_not_staged(self):
        self.assertEqual(module.select_observations([{**self.good,"sample_median_eur":float("nan")}],self.queue),[])
    def test_duplicate_idempotent(self):
        self.assertEqual(len(module.select_observations([self.good,self.good],self.queue)),1)

if __name__=="__main__":unittest.main()
