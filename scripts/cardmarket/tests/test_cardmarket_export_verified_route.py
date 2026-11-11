import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('export',source_path('export-cardmarket-full-queue.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ExportConfirmedRouteTests(unittest.TestCase):
 def test_exact_verified_id_takes_priority_over_old_candidates(self):
  self.assertIn("AND r.verification_state='VERIFIED_PRODUCT_ID'",m.SQL)
  self.assertIn('THEN r.provider_product_id',m.SQL)
  self.assertIn('END AS cardmarket_ids',m.SQL)
 def test_manual_refresh_survives_weekly_export(self):
  self.assertIn('manual_scan_requested_at',m.SQL)
  self.assertIn("r.source_evidence LIKE 'Human confirmed exact%'",m.SQL)
if __name__=='__main__':unittest.main()
