"""Session warmup must never bypass a blocked provider or normal cooldown."""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import unittest
from pathlib import Path
ROOT=Path(__file__).parent
class SessionWarmupTests(unittest.TestCase):
 def test_launcher_checks_cooldown_then_bootstraps_only_new_browser(self):
  s=(source_path('Cardmarket-Collector-Launcher.ps1')).read_text(encoding='utf-8-sig')
  order=[s.index("$diagnose=Join-Path"),s.index('CARDMARKET_COOLDOWN'),s.index("$warmupScript=Join-Path"),s.index('Start-Process -FilePath "powershell.exe"')]
  self.assertEqual(order,sorted(order))
  self.assertIn("if($browserNewlyStarted){\n  $warmupScript=",s)
  self.assertIn("if([string]$warmup.status -ne 'READY_FOR_HEALTH_CHECK')",s)
  self.assertIn("if([string]$health.status -ne 'AVAILABLE')",s)
  self.assertIn("CARDMARKET_PUBLIC_LIMITED_SESSION_CONTINUE",s)
  self.assertNotIn('"-RequireLogin"',s)
  self.assertIn("Get-CardmarketActiveCooldown",s)
  self.assertIn('"-BatchLimit","10"',s)
  self.assertIn('"-MinRequestGapSeconds","16"',s)
 def test_one_normal_navigation_six_seconds_no_challenge_bypass(self):
  s=(source_path('Cardmarket-Session-Warmup.ps1')).read_text(encoding='utf-8-sig')
  self.assertEqual(s.count("method='Page.navigate'"),1)
  self.assertIn("url='https://www.cardmarket.com/'",s)
  self.assertIn('Start-Sleep -Seconds 6',s)
  self.assertIn('if(!$page -and $AllowBlankBootstrap)',s)
  launcher=(source_path('Cardmarket-Collector-Launcher.ps1')).read_text(encoding='utf-8-sig')
  self.assertIn('\"about:blank\"',launcher)
  self.assertIn(' -AllowBlankBootstrap:$browserNewlyStarted',launcher)
  self.assertIn("$result.status='BLOCKED'",s)
  self.assertIn('READY_FOR_HEALTH_CHECK',s)
  self.assertNotIn('cf_clearance',s)
  self.assertNotIn('PHPSESSID',s)
  self.assertNotIn('captcha.solve',s.lower())
  self.assertNotIn('User_Login',s)
 def test_morning_script_never_runs_on_wrong_date_or_old_guide(self):
  s=(source_path('cardmarket-next-day-delta-20261112.py')).read_text()
  self.assertIn("!='2026-11-12'",s)
  self.assertIn('if not after or after<=before:',s)
  self.assertIn('dry_run=True',s)
  self.assertIn('PREVIEW_ONLY_SCANNER_ACTIVE',s)
  self.assertIn("guard.returncode",s)
if __name__=='__main__':unittest.main()
