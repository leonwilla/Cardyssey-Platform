import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("cm_import",source_path("import-cardmarket-browser-observations.py"))
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
    def test_new_complete_english_offer_is_staged_but_not_published(self):
        q=[{"cardyssey_karte":"mep-095","variante_id":"legacy:holo","cardmarket_ids":"895610","scan_tier":"2"}]
        obs={**self.good,"status":"COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED",
             "language":"en","verified_lang_nm_offers":26,"all_pages_complete":True,
             "access_mode":"AUTHENTICATED","sample_median_eur":1.86}
        rows=module.select_observations([obs],q)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["language_code"],"en")
        self.assertTrue(rows[0]["candidate"]["all_pages_complete"])
        self.assertTrue(rows[0]["candidate"]["no_verified_print_identity"])
        self.assertNotIn("tcg_price_cache",module.sql_for(rows))
    def test_public_limited_never_looks_complete(self):
        obs={**self.good,"language":"de","access_mode":"PUBLIC_LIMITED",
             "verified_lang_nm_offers":50,"all_pages_complete":False}
        rows=module.select_observations([obs],self.queue)
        self.assertFalse(rows[0]["candidate"]["all_pages_complete"])
    def test_complete_status_requires_completeness_flag(self):
        obs={**self.good,"status":"COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED",
             "verified_lang_nm_offers":26,"all_pages_complete":False}
        self.assertEqual(module.select_observations([obs],self.queue),[])
    def test_duplicate_idempotent(self):
        self.assertEqual(len(module.select_observations([self.good,self.good],self.queue)),1)

if __name__=="__main__":unittest.main()
