import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class LoginPausePolicyTests(unittest.TestCase):
 def test_runner_requires_login_and_stops_on_block(self):
  runner=(ROOT/'Cardmarket-Queue-Runner.ps1').read_text(encoding='utf-8-sig')
  self.assertIn('-RequireLogin:$RequireLogin',runner)
  self.assertIn("'LOGIN_REQUIRED'",runner)
  self.assertIn("'BLOCKED'",runner)
 def test_collector_stops_instead_of_scanning_as_guest(self):
  scanner=(ROOT/'cardmarket-language-browser-collector.ps1').read_text(encoding='utf-8-sig')
  self.assertIn("if ($RequireLogin -and -not $auth) { Assert-CardmarketAuthenticated }",scanner)
  self.assertIn("function Assert-CardmarketAuthenticated",scanner)
  self.assertIn("throw 'CARDMARKET_PROVIDER_CHALLENGE'",scanner)
  self.assertIn("Save-Progress $processed.Count $runTotal 'LOGIN_REQUIRED'",scanner)
  self.assertIn("Save-Progress $processed.Count $runTotal 'BLOCKED'",scanner)
 def test_resume_gate_does_not_retry_blocked_or_logged_out_session(self):
  launcher=(ROOT/'Cardmarket-Collector-Launcher.ps1').read_text(encoding='utf-8-sig')
  self.assertIn("$health.login -ne 'AUTHENTICATED'",launcher)
  self.assertIn("'LOGIN_UNVERIFIED'",launcher)
  self.assertIn('"-Languages","both"',launcher)
  self.assertIn('"-RequireLogin"',launcher)
 def test_manual_resume_does_not_override_access_gate(self):
  wrapper=(ROOT/'Cardmarket-Manual-Resume.ps1').read_text(encoding='utf-8-sig')
  self.assertIn('& $launcher -ManualResume',wrapper)
  self.assertNotIn('-ForcePublicMode',wrapper)
if __name__=='__main__':unittest.main()
