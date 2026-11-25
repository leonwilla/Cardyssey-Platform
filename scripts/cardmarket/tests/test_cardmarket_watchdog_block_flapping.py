"""A resume that runs straight into the next challenge must not reset the alert grace."""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import unittest


class WatchdogBlockFlappingTests(unittest.TestCase):
    def source(self):
        return source_path('Cardmarket-Resume-Watchdog.ps1').read_text(encoding='utf-8-sig')

    def test_clear_remembers_first_seen(self):
        s = self.source()
        self.assertIn("telegram-block-last-cleared.json", s)
        self.assertIn("clearedAt=[DateTime]::UtcNow.ToString('o')", s)

    def test_register_reuses_first_seen_inside_flap_window(self):
        s = self.source()
        self.assertIn("if($age -lt $BlockFlapMinutes -and $cleared.firstSeen){$first=[string]$cleared.firstSeen}", s)

    def test_alert_state_reset_only_after_quiet_window(self):
        s = self.source()
        self.assertIn("if(Test-CardmarketBlockResolved){Send-CardmarketTelegramAlert 'BLOCKED' $blockMessage $false}", s)


if __name__ == '__main__':
    unittest.main()
