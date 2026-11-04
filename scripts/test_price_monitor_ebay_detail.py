import unittest,importlib.util
from pathlib import Path
p=Path(__file__).with_name('price_monitor_ebay_detail.py')
spec=importlib.util.spec_from_file_location('detail',p)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DetailedMonitorTest(unittest.TestCase):
 def test_tannza_full_saved_evidence(self):
  data=module.evidence('sv01-001')
  self.assertEqual(data['totalSearchResults'],len(data['results']))
  self.assertEqual(sum(data['counts'].values()),data['totalSearchResults'])
  self.assertGreaterEqual(len(data['results']),8)
  self.assertGreaterEqual(len(data['offers']),7)
  self.assertTrue(any(len(o['transactions'])>5 for o in data['offers']))
  self.assertTrue(any(r['kind']=='CONFIRMED_SINGLE' for r in data['results']))
 def test_unsafe_card_id_rejected(self):
  for value in ('../sv01-001','sv01-001;DELETE',''):
   with self.assertRaises(ValueError):module.evidence(value)

if __name__=='__main__':unittest.main()
