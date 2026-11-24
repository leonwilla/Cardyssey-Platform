import unittest
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / 'core'


def src(name):
    return (CORE / name).read_text(encoding='utf-8-sig')


class HourlyClearanceTests(unittest.TestCase):
    """Cardmarket's Cloudflare clearance expires about every 60 minutes."""

    def test_collector_waits_passively_for_self_clearing_challenge(self):
        s = src('cardmarket-language-browser-collector.ps1')
        self.assertIn('[int]$ChallengeWaitSeconds = 120', s)
        self.assertIn('Start-Sleep -Milliseconds $(if($sawChallenge){5000}else{400})', s)
        self.assertNotIn('Input.dispatchMouseEvent', s)

    def test_session_status_only_fingerprints_clearance(self):
        s = src('Cardmarket-Session-Status.ps1')
        self.assertIn("method='Network.getCookies'", s)
        self.assertIn("$_.name -eq 'cf_clearance'", s)
        self.assertIn("$hash[0..7]", s)
        self.assertNotIn('Network.setCookie', s)
        self.assertNotIn('$state.clearance=', s)

    def test_watchdog_resumes_only_after_renewed_clearance(self):
        s = src('Cardmarket-Resume-Watchdog.ps1')
        self.assertIn('[int]$BlockedAlertGraceMinutes=5', s)
        self.assertIn('[int]$ClearanceWaitMinutes=30', s)
        self.assertIn('function Test-CardmarketClearanceRenewed', s)
        self.assertIn("Note 'CLEARANCE_NOT_RENEWED_WAITING'", s)
        i = s.index("Note 'CLEARANCE_NOT_RENEWED_WAITING'")
        self.assertLess(i, s.index("Note 'PAGE_AVAILABLE_ATTEMPT_RESUME'"))
        self.assertIn('F5', s)

    def test_launcher_keeps_login_across_restarts_without_cookie_access(self):
        s = src('Cardmarket-Collector-Launcher.ps1')
        self.assertIn("$data['session']['restore_on_startup']=1", s)
        self.assertIn(".cardyssey-backup", s)
        self.assertLess(s.index('restore_on_startup'), s.index('Start-Process $chrome'))


if __name__ == '__main__':
    unittest.main()
