import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('readiness',source_path('cardmarket-filter-readiness.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ReadinessTests(unittest.TestCase):
 def row(self,**changes):
  return {'set_id':'base1','kartennummer':'13','variante_id':'v1','drucktyp':'Holo','sonderdruck':'','stempel':'[]','foil':'',**changes}
 def test_normal_holo_not_reverse(self):
  x=m.analyze(self.row());self.assertEqual(x['reverse'],'N');self.assertEqual(x['missing'],[])
 def test_english_edition_stamp_is_recognized(self):
  x=m.analyze(self.row(stempel='["1st-edition"]'));self.assertEqual(x['firstEdition'],'Y');self.assertFalse(x['unsupported'])
 def test_quappo_1999_2000_copyright_needs_extra_evidence(self):
  x=m.analyze(self.row(sonderdruck='Copyright 1999-2000'));self.assertEqual(x['firstEdition'],'N');self.assertFalse(x['exactPrintFilterable']);self.assertEqual(x['unsupported'],['sonderdruck_nicht_filterbar'])
 def test_blank_core_field_is_reported_before_browser(self):
  self.assertIn('kartennummer',m.analyze(self.row(kartennummer=''))['missing'])
 def test_uncommon_print_needs_special_rule_not_false_card_missing(self):
  self.assertIn('drucktyp_nicht_im_standardfilter',m.analyze(self.row(drucktyp='lenticular'))['missing'])
if __name__=='__main__':unittest.main()
