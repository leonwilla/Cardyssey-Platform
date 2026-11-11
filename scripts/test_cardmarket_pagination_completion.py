"""Do not interpret a missing/stalled next-page load as a verified full market."""
import unittest
from pathlib import Path
SRC=(Path(__file__).with_name('cardmarket-language-browser-collector.ps1')).read_text(encoding='utf-8-sig')
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
  self.assertIn('$out.all_pages_complete=($auth',SRC)
 def test_median_requires_verified_full_market_and_all_offer_flags(self):
  self.assertIn('$out.median_all_offers_eur=if($out.all_pages_complete)',SRC)
  self.assertIn('$uniqueOfferIds.Count -ne [int]$data.totalRows',SRC)
  self.assertIn('$accepted.Count -ne [int]$data.totalRows',SRC)
  self.assertIn('MISMATCHED_OFFER_FILTER_FLAGS',SRC)
if __name__=='__main__':unittest.main()
