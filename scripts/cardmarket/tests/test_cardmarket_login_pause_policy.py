import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class LoginPausePolicyTests(unittest.TestCase):
 def test_runner_requires_login_and_stops_on_block(self):
  runner=(source_path('Cardmarket-Queue-Runner.ps1')).read_text(encoding='utf-8-sig')
  self.assertIn('-RequireLogin:$RequireLogin',runner)
  self.assertIn("'LOGIN_REQUIRED'",runner)
  self.assertIn("'BLOCKED'",runner)
 def test_collector_stops_instead_of_scanning_as_guest(self):
  scanner=(source_path('cardmarket-language-browser-collector.ps1')).read_text(encoding='utf-8-sig')
  self.assertIn("if ($RequireLogin -and -not $auth) { Assert-CardmarketAuthenticated }",scanner)
  self.assertIn("function Assert-CardmarketAuthenticated",scanner)
  self.assertIn("throw 'CARDMARKET_PROVIDER_CHALLENGE'",scanner)
  self.assertIn("Save-Progress $processed.Count $runTotal 'LOGIN_REQUIRED'",scanner)
  self.assertIn("Save-Progress $processed.Count $runTotal 'BLOCKED'",scanner)
 def test_resume_gate_blocks_unavailable_provider_but_allows_guests(self):
  launcher=(source_path('Cardmarket-Collector-Launcher.ps1')).read_text(encoding='utf-8-sig')
  self.assertIn("$health.login -ne 'AUTHENTICATED'",launcher)
  self.assertIn("if($browserNewlyStarted -and $health.status -eq 'BLOCKED')",launcher)
  self.assertIn('"-Languages","both"',launcher)
  self.assertNotIn('"-RequireLogin"',launcher)
  self.assertIn("CARDMARKET_PUBLIC_LIMITED_SESSION_CONTINUE",launcher)
  self.assertIn("if([string]$health.status -ne 'AVAILABLE')",launcher)
 def test_streak_policy_shared_between_runner_launcher_watchdog(self):
  policy=(source_path('Cardmarket-Backoff-Policy.ps1')).read_text(encoding='utf-8-sig')
  for name in ('Cardmarket-Collector-Launcher.ps1','Cardmarket-Resume-Watchdog.ps1'):
   text=(source_path(name)).read_text(encoding='utf-8-sig')
   self.assertIn('Cardmarket-Backoff-Policy.ps1',text)
   self.assertIn('Get-CardmarketCooldownMinutes',text)
  runner=(source_path('Cardmarket-Queue-Runner.ps1')).read_text(encoding='utf-8-sig')
  self.assertIn('Update-CardmarketBlockedStreak',runner)
  self.assertIn('cardmarket-blocked-streak.json',policy)
  self.assertIn("$streak -eq 1 -and $ProviderStatus -eq 'AVAILABLE'",policy)
  self.assertIn('return 30',policy)
  self.assertIn('return 240',policy)
 def test_manual_resume_does_not_override_access_gate(self):
  wrapper=(source_path('Cardmarket-Manual-Resume.ps1')).read_text(encoding='utf-8-sig')
  self.assertIn('& $launcher -ManualResume',wrapper)
  self.assertNotIn('-ForcePublicMode',wrapper)
  launcher=(source_path('Cardmarket-Collector-Launcher.ps1')).read_text(encoding='utf-8-sig')
  self.assertNotIn('if (-not $ManualResume)',launcher)
  self.assertIn('CARDMARKET_COOLDOWN',launcher)
if __name__=='__main__':unittest.main()
