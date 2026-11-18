"""Windows reboot must not strand Cardmarket when dedicated Edge is closed."""
import unittest
from pathlib import Path

SRC=Path(__file__).resolve().parents[1]/"core"
class RebootRecoveryPolicyTests(unittest.TestCase):
    def test_unavailable_edge_bootstraps_only_after_cooldown(self):
        s=(SRC/"Cardmarket-Resume-Watchdog.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("$browserNeedsBootstrap=([string]$diag.status -eq 'BROWSER_UNAVAILABLE')",s)
        self.assertLess(s.index("foreach($s in $remaining)"),s.index("if($browserNeedsBootstrap){"))
        self.assertIn("Note 'BROWSER_COLD_START_AFTER_COOLDOWN'",s)
        self.assertIn("& $launcher -ResumeAfterClearance",s)
        self.assertIn("Get-CardmarketCooldownMinutes",s)
        self.assertIn("Get-CardmarketCooldownMinutes",s)
    def test_blocked_login_required_unknown_state_fail_closed(self):
        s=(SRC/"Cardmarket-Resume-Watchdog.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("if(!(Test-Path $checker)){Note 'SESSION_CHECKER_MISSING';return}",s)
        self.assertIn("if($diag.status -eq 'BLOCKED'){Note 'CHALLENGE_STILL_PRESENT';return}",s)
        self.assertIn("CARDMARKET_GUEST_SESSION_AVAILABLE",s)
        self.assertIn("if(!$browserNeedsBootstrap -and $diag.status -ne 'AVAILABLE')",s)
        self.assertNotIn("CARDMARKET_LOGIN_REQUIRED';return",s)
        self.assertIn("if(!(Test-Path $launcher)){Note 'COLLECTOR_LAUNCHER_MISSING';return}",s)
    def test_launcher_still_verifies_login_and_uses_pacing(self):
        s=(SRC/"Cardmarket-Collector-Launcher.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("Cardmarket-Session-Warmup.ps1",s)
        self.assertIn("if([string]$health.status -ne 'AVAILABLE')",s)
        self.assertIn("CARDMARKET_PUBLIC_LIMITED_SESSION_CONTINUE",s)
        self.assertIn('"-BatchLimit","16"',s)
        self.assertIn('"-MinRequestGapSeconds","13"',s)

if __name__=="__main__":unittest.main()
