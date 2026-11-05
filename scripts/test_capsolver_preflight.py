import importlib.util, unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('capsolver_preflight',Path(__file__).with_name('capsolver_preflight.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class PreflightTest(unittest.TestCase):
 def test_missing_key_never_creates_task(self):
  with patch.dict('os.environ',{},clear=True),patch.object(module,'KEYFILE',Path('/unlikely-capsolver-key-absent')):
   result=module.preflight()
   self.assertEqual(result['status'],'MISSING_API_KEY')
   self.assertFalse(result['taskCreated'])
 def test_get_balance_is_only_api_called(self):
  class Response:
   def raise_for_status(self):pass
   def json(self):return {'errorId':0,'balance':0.5,'packages':[]}
  with patch.dict('os.environ',{'CAPSOLVER_API_KEY':'dummy'}),patch.object(module.requests,'post',return_value=Response()) as req:
   result=module.preflight()
   self.assertEqual(result['status'],'API_ACCEPTED')
   self.assertEqual(req.call_args.args[0],'https://api.capsolver.com/getBalance')
   self.assertFalse(result['taskCreated'])
if __name__=='__main__':unittest.main()
