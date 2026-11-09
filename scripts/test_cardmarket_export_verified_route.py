import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('export',Path(__file__).with_name('export-cardmarket-full-queue.py'))
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
