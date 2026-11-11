#!/usr/bin/env python3
"""Regression checks against actual queued Cardyssey print variants."""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv
import re
import unittest
from pathlib import Path

QUEUE=Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector/queue-de.csv")
SCRIPT=source_path("cardmarket-language-browser-collector.ps1")

def filters(row):
    kind=row["drucktyp"]
    reverse="Y" if re.search("reverse",kind,re.I) else "N" if re.search("normal",kind,re.I) else "0"
    stamp=row["stempel"]
    first="Y" if re.search(r"1\. auflage|first.edition",stamp,re.I) else (
        "N" if re.fullmatch(r"unbegrenzt|unlimited",row["sonderdruck"],re.I) else "0")
    return reverse,first
def selected():
    wanted={"base1-8","sm10-16","mep-095"}
    with QUEUE.open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            if r["cardyssey_karte"] in wanted:yield r

class CheckVariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=list(selected())
    def test_first_edition_machamp(self):
        rows=[r for r in self.rows if r["cardyssey_karte"]=="base1-8" and "1. Auflage" in r["stempel"]]
        self.assertEqual(len(rows),1)
        self.assertEqual(filters(rows[0]),("0","Y"))
    def test_unlimited_machamp(self):
        rows=[r for r in self.rows if r["cardyssey_karte"]=="base1-8" and r["sonderdruck"]=="unbegrenzt"]
        self.assertEqual(len(rows),1)
        self.assertEqual(filters(rows[0]),("0","N"))
    def test_tangela_reverse_does_not_imply_first(self):
        rows=[r for r in self.rows if r["cardyssey_karte"]=="sm10-16" and "reverse" in r["drucktyp"].lower()]
        self.assertEqual(len(rows),1)
        self.assertEqual(filters(rows[0]),("Y","0"))
    def test_tangela_normal(self):
        rows=[r for r in self.rows if r["cardyssey_karte"]=="sm10-16" and "normal" in r["drucktyp"].lower()]
        self.assertEqual(len(rows),1)
        self.assertEqual(filters(rows[0]),("N","0"))
    def test_lucario_not_auto_cosmos_filter(self):
        rows=[r for r in self.rows if r["cardyssey_karte"]=="mep-095"]
        self.assertEqual(len(rows),1)
        self.assertEqual(filters(rows[0]),("0","0"))
    def test_pagination_requires_full_and_unique_offer_ids(self):
        s=SCRIPT.read_text(encoding="utf-8-sig")
        for marker in (
            "loadMoreButton", "LOAD_MORE_NO_NEW_OFFERS", "LOAD_MORE_DISABLED_OR_LIMIT_REACHED",
            "CARDMARKET_COLLECTOR_CAP", "DUPLICATE_OR_MISSING_OFFER_ID",
            "MISMATCHED_OFFER_FILTER_FLAGS", "all_pages_complete",
            "median_all_offers_eur", "totalRows",
        ):
            self.assertIn(marker,s)
    def test_search_cache_only_reuses_search_links_not_filtered_offers(self):
        s=SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn('$searchCache.ContainsKey($searchUrl)',s)
        self.assertIn('$searchCache[$searchUrl] = $links',s)
        self.assertIn('$out.search_cache_hit=$true',s)
        self.assertIn('search_cache_hits = $searchCacheHits',s)
        self.assertIn('DEFERRED_PROVIDER_TIMEOUT',s)
        self.assertNotIn('$searchCache[$key] = $accepted',s)
    def test_elapsed_ms_collected_without_changing_filters(self):
        s=SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn('$caseTimer=[Diagnostics.Stopwatch]::StartNew()',s)
        self.assertIn('$out.elapsed_ms=[int]$caseTimer.ElapsedMilliseconds',s)
        self.assertIn('extra[isReverseHolo]',s)
    def test_priced_bulk_is_routed_to_feed_not_browser(self):
        s=SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn("$bulkFeedOnlyRows=@($allCases | Where-Object {",s)
        self.assertIn("$priceNeeded = [string]$case.scan_tier -ne '4'",s)
        self.assertIn("bulk_feed_only_variants = $bulkFeedOnly",s)
    def test_batch_has_pending_limit_and_resume(self):
        s=SCRIPT.read_text(encoding="utf-8-sig")
        for token in ("[int]$BatchLimit = 0", "-not $processed.Contains($k)", "Select-Object -First $BatchLimit", "BATCH_COMPLETE_MORE_PENDING"):
            self.assertIn(token,s)
    def test_qc_reports_complete_prices_as_print_unverified(self):
        s=SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn("complete_filtered_asking_medians_print_unverified",s)
        self.assertIn("verified_language_variant_prices = 0",s)
    def test_public_session_fails_closed_and_continues(self):
        s=SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn("access_mode='UNKNOWN'",s)
        self.assertIn("'PUBLIC_LIMITED'",s)
        self.assertIn('a[href*=User_Logout]',s)
        self.assertIn("PUBLIC_SESSION_LIMITED_SAMPLE",s)
        self.assertIn("$auth -and $data.filtered",s)
        self.assertIn("Save-Progress $processed.Count $runTotal 'LOGIN_REQUIRED'",s)
        self.assertIn("if ($RequireLogin -and -not $auth) { Assert-CardmarketAuthenticated }",s)
        self.assertIn("throw 'CARDMARKET_LOGIN_REQUIRED'",s)
        self.assertIn("throw 'CARDMARKET_PROVIDER_CHALLENGE'",s)
        self.assertIn("if ($data.filtered -and $auth)",s)
    def test_verified_queue_mapping_precedes_unreliable_text_search(self):
        s=SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn("$case.known_url",s)
        self.assertIn("$case.routing_state -eq 'VERIFIED_PRODUCT_ID'",s)
        self.assertIn("$out.product_id = $candidateId",s)
        self.assertIn("PRODUCT_ID_NOT_IN_VERIFIED_SET",s)
    def test_live_script_independent_filters_and_query_verification(self):
        s=SCRIPT.read_text(encoding="utf-8-sig")
        for token in ("expected_reverse_holo","expected_first_edition","extra[isReverseHolo]","extra[isFirstEd]","searchParams.get(k)","all_pages_complete=$false"):
            self.assertIn(token,s)
if __name__=="__main__":
    unittest.main()
