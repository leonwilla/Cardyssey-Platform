import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import importlib.util,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
s=importlib.util.spec_from_file_location('cmprice',source_path('import-cardmarket-filtered-prices.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class FilteredImportTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)/'observations.jsonl'
  self.x={'language':'de','card_id':'a','variant_id':'v','product_id':'123',
   'url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/Set/A-V1-N?language=3&minCondition=2&isReverseHolo=N&isFirstEd=N',
   'identity_confirmed':True,'status':'COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED',
   'all_pages_complete':True,'median_all_offers_eur':1.25,'verified_lang_nm_offers':6,
   'expected_reverse_holo':'N','expected_first_edition':'N','seen_at':datetime.now(timezone.utc).isoformat()}
 def run_case(self,**changes):
  a={**self.x,**changes};self.p.write_text(json.dumps(a)+'\n');return m.collect(self.p,'de')
 def test_full_explicit_filter_is_eligible_for_human_route_join(self):
  self.assertEqual(len(self.run_case()),1)
 def test_incomplete_market_sample_never_publishes(self):
  self.assertEqual(self.run_case(all_pages_complete=False),[])
 def test_missing_first_ed_filter_never_publishes(self):
  self.assertEqual(self.run_case(url=self.x['url'].split('&isFirstEd')[0]),[])
 def test_wrong_language_never_publishes(self):
  self.assertEqual(self.run_case(language='en'),[])
 def test_db_requires_human_print_validation(self):
  self.assertIn("source_evidence LIKE 'Human confirmed exact%'",m.SQL)
  self.assertIn('VERIFIED_PRODUCT_ID',m.SQL)
if __name__=='__main__':unittest.main()
