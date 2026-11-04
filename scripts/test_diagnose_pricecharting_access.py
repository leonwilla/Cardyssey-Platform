import importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).with_name('diagnose-pricecharting-access.py')
spec=importlib.util.spec_from_file_location('pricecharting_health',p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PricechartingAccessTests(unittest.TestCase):
 def test_untrusted_subdomain_never_enables_import(self):
  def fake(url):return {'status':'TLS_CERTIFICATE_INVALID'} if 'ae.' in url else {'status':'CHALLENGE_OR_FORBIDDEN','httpStatus':403}
  with patch.dict('os.environ',{'PRICECHARTING_API_KEY':''}):
   out=mod.preflight(fake)
   self.assertEqual(out['suggestedSubdomain']['status'],'TLS_CERTIFICATE_INVALID')
   self.assertFalse(out['apiImportPrerequisitesMet'])
   self.assertEqual(out['recommendation'],'NEEDS_LICENSED_API_ACCESS_AND_VERIFIED_PRODUCT_IDS')
 def test_no_shared_cookies_used_by_probe(self):
  import inspect
  code=inspect.getsource(mod.probe)
  self.assertNotIn('Cookie',code)
  self.assertNotIn('CERT_NONE',code)
  self.assertNotIn('verify=False',code)

if __name__=='__main__':unittest.main()
