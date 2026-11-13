"""Do not interpret a missing/stalled next-page load as a verified full market."""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import unittest
from pathlib import Path
SRC=(source_path('cardmarket-language-browser-collector.ps1')).read_text(encoding='utf-8-sig')
class PaginationTests(unittest.TestCase):
 def test_at_most_three_load_more_pages_without_false_completeness(self):
  self.assertIn('$offerCap=1200',SRC)
  self.assertIn('$maxOfferPages=3',SRC)
  self.assertIn('.slice(0,1200)',SRC)
  self.assertIn('if($data.hasMore -and !$out.pagination_failure)',SRC)
  self.assertIn("$out.pagination_failure='MORE_OFFERS_STILL_VISIBLE'",SRC)
  self.assertNotIn('CARDMARKET_300_CAP',SRC)
 def test_only_stable_absent_button_can_convert_old_error_to_complete(self):
  self.assertIn("$lastButton -ne 'ABSENT'",SRC)
  self.assertIn('BUTTON_REMOVED_STABLE_4_CHECKS',SRC)
  self.assertIn('if($stableEnd)',SRC)
  self.assertIn('if($settle -eq 3)',SRC)
  self.assertNotIn("if($clicked -eq 'DISABLED') {$out.pagination_failure=''}",SRC)
 def test_stop_is_always_incomplete_if_offer_cap_or_visible_more(self):
  self.assertIn("$out.pagination_failure='CARDMARKET_COLLECTOR_CAP'",SRC)
  self.assertIn("$out.pagination_failure='MORE_OFFERS_STILL_VISIBLE'",SRC)
  self.assertIn('not $data.hasMore',SRC)
  self.assertIn('$out.all_pages_complete=($data.filtered',SRC)
  self.assertIn("($auth -or [int]$data.totalRows -le 25)",SRC)
  self.assertIn('GUEST_MORE_THAN_25_ROWS_UNVERIFIED',SRC)
  self.assertIn('DEFERRED_LOGIN_REQUIRED',SRC)
 def test_median_requires_verified_full_market_and_all_offer_flags(self):
  self.assertIn('$out.median_all_offers_eur=if($out.all_pages_complete)',SRC)
  self.assertIn('$uniqueOfferIds.Count -ne [int]$data.totalRows',SRC)
  self.assertIn('$accepted.Count -ne [int]$data.totalRows',SRC)
  self.assertIn('MISMATCHED_OFFER_FILTER_FLAGS',SRC)
if __name__=='__main__':unittest.main()
