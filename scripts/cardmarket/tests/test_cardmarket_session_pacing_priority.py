"""Safeguards for persistent profile, provider cooldown, and paced requests."""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class SessionPacingPolicyTests(unittest.TestCase):
 def source(self,name):
  return (source_path(name)).read_text(encoding='utf-8-sig')
 def test_persistent_profile_no_cookie_replay(self):
  launcher=self.source('Cardmarket-Collector-Launcher.ps1')
  self.assertIn('CardmarketEdgeProfile',launcher)
  self.assertIn('--user-data-dir=$profile',launcher)
  self.assertIn('Cardmarket-Session-Status.ps1',launcher)
  for token in ['PHPSESSID','browser-cookie3','storage_state','Set-Cookie','CookieHeader']:
   self.assertNotIn(token,launcher)
  self.assertNotIn('$cookies=',launcher)
 def test_per_request_budget_including_ajax(self):
  scanner=self.source('cardmarket-language-browser-collector.ps1')
  self.assertIn('[int]$MinRequestGapSeconds = 16',scanner)
  self.assertIn('function Wait-CardmarketRequestBudget',scanner)
  self.assertIn("$script:lastProviderRequestUtc=[DateTime]::MinValue",scanner)
  self.assertIn("Wait-CardmarketRequestBudget\n  Send-Cdp 'Page.navigate'",scanner)
  self.assertIn("Wait-CardmarketRequestBudget\n          Send-Cdp 'Page.navigate'",scanner)
  self.assertIn("Wait-CardmarketRequestBudget\n                $clicked=Js",scanner)
  self.assertIn("Wait-CardmarketRequestBudget\n            $filterOk = Js",scanner)
 def test_runner_shares_gap_with_both_languages(self):
  runner=self.source('Cardmarket-Queue-Runner.ps1')
  self.assertIn('MinRequestGapSeconds $MinRequestGapSeconds',runner)
  self.assertIn('BatchLimit = 10',runner)
  self.assertIn('RunMinutes = 40',runner)
  self.assertIn('Start-Sleep -Seconds $MinRequestGapSeconds',runner)
  launcher=self.source('Cardmarket-Collector-Launcher.ps1')
  self.assertIn('"-BatchLimit","10"',launcher)
  self.assertIn('"-MinRequestGapSeconds","16"',launcher)
  self.assertIn('"-Languages","both","-SingleBatch"',launcher)
  self.assertIn('[int]$ChallengeWaitSeconds = 15',self.source('cardmarket-language-browser-collector.ps1'))
  self.assertIn('return 20',self.source('Cardmarket-Backoff-Policy.ps1'))
  self.assertIn('& $watchdog -ReportBlocked',runner)
 def test_backoff_persists_between_runner_invocations(self):
  for name in ('Cardmarket-Collector-Launcher.ps1','Cardmarket-Resume-Watchdog.ps1'):
   source=self.source(name)
   self.assertIn("Get-CardmarketActiveCooldown",source)
   self.assertIn("Get-CardmarketActiveCooldown",source)
   self.assertNotIn("'LOGIN_REQUIRED' {20;break}",source)
  watchdog=self.source('Cardmarket-Resume-Watchdog.ps1')
  self.assertIn("foreach($language in @('de','en'))",watchdog)
  self.assertIn("if(!$browserNeedsBootstrap -and $diag.status -ne 'AVAILABLE')",watchdog)
 def test_access_denied_not_mislabeled_logout(self):
  status=self.source('Cardmarket-Session-Status.ps1')
  scanner=self.source('cardmarket-language-browser-collector.ps1')
  self.assertIn('you have been blocked',status)
  self.assertIn('you have been blocked',scanner)
  self.assertIn('Assert-CardmarketAuthenticated',scanner)
  self.assertIn('CARDMARKET_PROVIDER_CHALLENGE',scanner)
if __name__=='__main__':unittest.main()
