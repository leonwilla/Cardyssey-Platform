#!/usr/bin/env python3
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("cm_import",source_path("import-cardmarket-mapping-safe.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SafeMappingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"browser.jsonl"
        self.queue={("card-a","var-a"):{"cardmarket_ids":"1234,5678","known_url":""}}
    def test_verified_browser_identity_maps_only_source_evidence(self):
        rec={"card_id":"card-a","variant_id":"var-a","language":"de",
             "identity_confirmed":True,"product_id":"1234",
             "url":"https://www.cardmarket.com/de/Pokemon/Products/Singles/SomeSet/SomeCard",
             "status":"MAPPED_NO_PRICE_REQUIRED"}
        self.path.write_text(json.dumps(rec)+"\n")
        rows,reasons=module.collect([self.path],self.queue,"de")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["product_id"],"1234")
    def test_candidate_mismatch_rejected(self):
        rec={"card_id":"card-a","variant_id":"var-a","language":"de",
             "identity_confirmed":True,"product_id":"9999",
             "url":"https://www.cardmarket.com/de/Pokemon/Products/Singles/Set/Card"}
        self.path.write_text(json.dumps(rec)+"\n")
        rows,reasons=module.collect([self.path],self.queue,"de")
        self.assertEqual(rows,[])
        self.assertEqual(reasons["ID_NOT_IN_CANDIDATES"],1)
    def test_wrong_language_rejected(self):
        rec={"card_id":"card-a","variant_id":"var-a","language":"en",
             "identity_confirmed":True,"product_id":"1234",
             "url":"https://www.cardmarket.com/en/Pokemon/Products/Singles/Set/Card"}
        self.path.write_text(json.dumps(rec)+"\n")
        rows,_=module.collect([self.path],self.queue,"de")
        self.assertEqual(rows,[])
    def test_wrong_verified_set_slug_rejected(self):
        self.queue[('card-a','var-a')]['set_id']='base1'
        rec={'card_id':'card-a','variant_id':'var-a','language':'de',
             'identity_confirmed':True,'product_id':'1234',
             'url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/Expansion-Pack/Machamp-EXP'}
        self.path.write_text(json.dumps(rec)+'\n')
        rows,reasons=module.collect([self.path],self.queue,'de',{'base1':'Base-Set'})
        self.assertEqual(rows,[])
        self.assertEqual(reasons['WRONG_CARDMARKET_SET'],1)
    def test_no_browser_confirmation_rejected(self):
        rec={"card_id":"card-a","variant_id":"var-a","language":"de",
             "identity_confirmed":False,"product_id":"1234",
             "url":"https://www.cardmarket.com/de/Pokemon/Products/Singles/Set/Card"}
        self.path.write_text(json.dumps(rec)+"\n")
        rows,_=module.collect([self.path],self.queue,"de")
        self.assertEqual(rows,[])
    def test_human_confirmed_missing_url_filled_only_for_matching_id(self):
        source=source_path('import-cardmarket-mapping-safe.py').read_text()
        self.assertIn("p.verification_state='VERIFIED_PRODUCT_ID'",source)
        self.assertIn('p.provider_product_id=s.pid',source)
        self.assertIn("p.source_evidence LIKE 'Human confirmed exact%'",source)
    def test_protects_existing_verified_data(self):
        self.assertIn("verification_state='SOURCE_ONLY'",module.SQL)
        self.assertIn("primary_provider='CARDMARKET'",module.SQL)
        self.assertIn("ON CONFLICT (language_code,card_id,variant_id)",module.SQL)
if __name__=="__main__":
    unittest.main()
