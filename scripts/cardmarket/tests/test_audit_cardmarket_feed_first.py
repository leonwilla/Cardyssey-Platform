import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import unittest
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('cm_feed_first',source_path('audit-cardmarket-feed-first.py'))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
classify,audit=mod.classify,mod.audit

class FeedFirstTests(unittest.TestCase):
    row={'cardyssey_karte':'x','variante_id':'v','cardmarket_ids':'123','routing_state':'VERIFIED_PRODUCT_ID','drucktyp':'Normal','sonderdruck':'','foil':'','stempel':'[]'}
    guide={'123':{'avg30':1.25,'avg30-holo':2.5}}
    def test_simple_verified_preview(self):
        status,result=classify(self.row,self.guide)
        self.assertEqual(status,'VERIFIED_PRODUCT_GUIDE_PREVIEW')
        self.assertEqual(result['aggregate_eur'],1.25)
    def test_holo_bucket(self):
        status,result=classify({**self.row,'drucktyp':'Reverse'},self.guide)
        self.assertEqual(result['guide_bucket'],'avg30-holo')
    def test_holo_is_not_automatically_reverse_holo(self):
        status,result=classify({**self.row,'drucktyp':'Holo'},self.guide)
        self.assertEqual(status,'VERIFIED_PRODUCT_GUIDE_PREVIEW')
        self.assertEqual(result['guide_bucket'],'avg30')
    def test_candidate_not_verified(self):
        self.assertEqual(classify({**self.row,'routing_state':'SOURCE_ONLY'},self.guide)[0],'SINGLE_ID_NEEDS_IDENTITY_VERIFICATION')
    def test_special_never_auto(self):
        self.assertEqual(classify({**self.row,'stempel':'["staff"]'},self.guide)[0],'SPECIAL_PRINT_NEEDS_REVIEW')
    def test_multiple_not_assumed(self):
        self.assertEqual(classify({**self.row,'cardmarket_ids':'123,456'},self.guide)[0],'MULTIPLE_PRODUCT_IDS')
    def test_missing_id(self):
        self.assertEqual(classify({**self.row,'cardmarket_ids':''},self.guide)[0],'NO_PRODUCT_ID')
    def test_aggregate_counts(self):
        stats,quotes=audit([self.row,{**self.row,'cardmarket_ids':''}],self.guide)
        self.assertEqual(stats['NO_PRODUCT_ID'],1)
        self.assertEqual(len(quotes),1)
if __name__=='__main__':unittest.main()
