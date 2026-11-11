"""Session warmup must never bypass a blocked provider or normal cooldown."""
import unittest
from pathlib import Path
ROOT=Path(__file__).parent
class SessionWarmupTests(unittest.TestCase):
 def test_launcher_order_cooldown_then_warmup_then_health_then_runner(self):
  s=(ROOT/'Cardmarket-Collector-Launcher.ps1').read_text(encoding='utf-8-sig')
  order=[s.index('CARDMARKET_COOLDOWN'),s.index("$warmupScript=Join-Path"),s.index("$diagnose=Join-Path"),s.index('Start-Process -FilePath "powershell.exe"')]
  self.assertEqual(order,sorted(order))
  self.assertIn("if([string]$warmup.status -ne 'READY_FOR_HEALTH_CHECK')",s)
  self.assertIn("$health.status -ne 'AVAILABLE' -or $health.login -ne 'AUTHENTICATED'",s)
  self.assertIn("'BLOCKED' {240;break}",s)
  self.assertIn('"-BatchLimit","16"',s)
  self.assertIn('"-MinRequestGapSeconds","10"',s)
 def test_one_normal_navigation_six_seconds_no_challenge_bypass(self):
  s=(ROOT/'Cardmarket-Session-Warmup.ps1').read_text(encoding='utf-8-sig')
  self.assertEqual(s.count("method='Page.navigate'"),1)
  self.assertIn("url='https://www.cardmarket.com/'",s)
  self.assertIn('Start-Sleep -Seconds 6',s)
  self.assertIn('if(!$page -and $AllowBlankBootstrap)',s)
  launcher=(ROOT/'Cardmarket-Collector-Launcher.ps1').read_text(encoding='utf-8-sig')
  self.assertIn('\"about:blank\"',launcher)
  self.assertIn(' -AllowBlankBootstrap:$browserNewlyStarted',launcher)
  self.assertIn("$result.status='BLOCKED'",s)
  self.assertIn('READY_FOR_HEALTH_CHECK',s)
  self.assertNotIn('cf_clearance',s)
  self.assertNotIn('PHPSESSID',s)
  self.assertNotIn('captcha.solve',s.lower())
  self.assertNotIn('User_Login',s)
 def test_morning_script_never_runs_on_wrong_date_or_old_guide(self):
  s=(ROOT/'cardmarket-next-day-delta-20261112.py').read_text()
  self.assertIn("!='2026-11-12'",s)
  self.assertIn('if not after or after<=before:',s)
  self.assertIn('dry_run=True',s)
  self.assertIn('PREVIEW_ONLY_SCANNER_ACTIVE',s)
  self.assertIn("guard.returncode",s)
if __name__=='__main__':unittest.main()
