import re
import unittest
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / 'core'


class RefreshTierTests(unittest.TestCase):
    def setUp(self):
        self.collector = (CORE / 'cardmarket-language-browser-collector.ps1').read_text(encoding='utf-8-sig')
        self.policy = (CORE / 'Cardmarket-Backoff-Policy.ps1').read_text(encoding='utf-8-sig')

    def test_value_tiers_daily_weekly_four_weeks(self):
        body = re.search(r'function Get-CardmarketRefreshDays.*?\n}', self.collector, re.S).group(0)
        self.assertIn('if ($price -ge 250) { return 1 }', body)
        self.assertIn('if ($price -ge 100) { return 7 }', body)
        self.assertIn('return 28', body)

    def test_refresh_applies_inside_full_rescan_epoch(self):
        self.assertIn('$processedThisEpoch=($seen -ge $fullRecheckAfter -and $isRecent', self.collector)

    def test_due_cases_sorted_by_value_within_tier(self):
        self.assertIn("Sort-Object Tier,@{Expression='Price';Descending=$true},Index", self.policy)


if __name__ == '__main__':
    unittest.main()
