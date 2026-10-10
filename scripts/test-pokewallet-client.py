#!/usr/bin/env python3
"""Verify persistent quota enforcement, private keys and redacted failures."""
import importlib.util,io,json,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location("wallet",Path(__file__).with_name("pokewallet-client.py"));wallet=importlib.util.module_from_spec(s);s.loader.exec_module(wallet)
class Response(io.BytesIO):
 headers={}
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.key=self.root/"key";self.key.write_text("pk_live_test_not_a_real_key");self.key.chmod(0o600)
  self.client=wallet.Client(self.key,self.root/"state",hour_budget=2,day_budget=3)
 def tearDown(self):self.temp.cleanup()
 def response(self):return Response(b'{"success":true,"data":[]}')
 def test_authenticated_request_and_shared_budget(self):
  with patch.object(wallet.urllib.request,"urlopen",side_effect=lambda *a,**k:self.response()) as call:
   self.client.get("/sets");wallet.Client(self.key,self.root/"state",2,3).get("/sets")
   with self.assertRaisesRegex(wallet.ProviderError,"budget exhausted"):self.client.get("/sets")
   self.assertEqual(call.call_count,2)
   self.assertEqual(call.call_args.args[0].get_header("X-api-key"),self.key.read_text())
  ledger=self.root/"state"/"budget.json"
  self.assertEqual(ledger.stat().st_mode&0o077,0)
  self.assertNotIn(self.key.read_text(),ledger.read_text())
 def test_day_budget_survives_hour_boundary(self):
  ledger=self.root/"state"/"budget.json"
  with patch.object(wallet.time,"time",return_value=100000):
   ledger.write_text(json.dumps({"requests":[90000,91000,92000]}))
   with self.assertRaisesRegex(wallet.ProviderError,"budget exhausted"):self.client.get("/sets")
 def test_http_error_body_never_disclosed(self):
  error=urllib.error.HTTPError("https://api.pokewallet.io",401,self.key.read_text(),{},None)
  with patch.object(wallet.urllib.request,"urlopen",side_effect=error):
   with self.assertRaisesRegex(wallet.ProviderError,"HTTP 401") as result:self.client.get("/sets")
   self.assertNotIn(self.key.read_text(),str(result.exception))
 def test_rate_limit_persists_across_clients(self):
  error=urllib.error.HTTPError("https://api.pokewallet.io",429,"private body",{},None)
  with patch.object(wallet.urllib.request,"urlopen",side_effect=error) as call:
   with self.assertRaisesRegex(wallet.ProviderError,"HTTP 429"):self.client.get("/sets")
   with self.assertRaisesRegex(wallet.ProviderError,"rate limit active"):wallet.Client(self.key,self.root/"state",2,3).get("/sets")
   self.assertEqual(call.call_count,1)
 def test_public_key_file_rejected_before_network(self):
  self.key.chmod(0o644)
  with patch.object(wallet.urllib.request,"urlopen") as call:
   with self.assertRaisesRegex(wallet.ProviderError,"0600"):self.client.get("/sets")
   call.assert_not_called()
 def test_host_override_rejected(self):
  with self.assertRaises(ValueError):self.client.get("https://example.com")
  with self.assertRaises(ValueError):self.client.get("/sets?api_key=value")
 def test_free_budget_reserve(self):
  with self.assertRaises(ValueError):wallet.Client(self.key,self.root/"state",101,900)
 def test_inventory_does_not_infer_image_language(self):
  with patch.object(self.client,"get",return_value={"success":True,"data":[{"language":"jap","images":{"languages":["en"]}}]}):
   report=wallet.inventory(self.client);self.assertEqual(report["provider_language_codes"],{"jap":1})
if __name__=="__main__":unittest.main()
