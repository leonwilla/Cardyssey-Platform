import csv
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "scripts/cardmarket/core"
P = CORE / "cardmarket-language-browser-collector.ps1"
LAUNCHER = CORE / "Cardmarket-Collector-Launcher.ps1"
WATCHDOG = CORE / "Cardmarket-Resume-Watchdog.ps1"


def load_resolver():
    path = CORE / "resolve-multiple-search-hits.py"
    spec = importlib.util.spec_from_file_location("cm_resolver_guest", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GuestFetchUpgradeTests(unittest.TestCase):
    def test_product_fetch_persists_inert_dom_and_reads_no_second_navigation(self):
        s = P.read_text(encoding="utf-8-sig")
        self.assertIn('fetch(target,{credentials:"include",redirect:"follow"})', s)
        self.assertIn('new DOMParser().parseFromString(html,"text/html")', s)
        self.assertIn('window.__cardysseyFetchedProduct={doc,url:response.url}', s)
        self.assertIn("function Js-CardmarketProduct", s)
        self.assertIn("$out.product_load_mode='SAME_ORIGIN_FETCH_DOMPARSER'", s)
        self.assertIn("$out.product_load_mode='SAME_ORIGIN_FETCH_FILTERED_DOMPARSER'", s)
        self.assertIn("if(-not $script:cmFetchedProductActive){", s)
        self.assertIn("if($data.filtered -and $data.hasMore -and $auth -and $script:cmFetchedProductActive)", s)

    def test_guest_waits_only_when_provider_blocks_and_never_paginates(self):
        s = P.read_text(encoding="utf-8-sig")
        launcher = LAUNCHER.read_text(encoding="utf-8-sig")
        watchdog = WATCHDOG.read_text(encoding="utf-8-sig")
        self.assertIn("if($result.status -eq 'BLOCKED'){throw 'CARDMARKET_PROVIDER_CHALLENGE'}", s)
        self.assertIn("if (-not $auth -and $data.hasMore) { $out.pagination_failure='DEFERRED_LOGIN_REQUIRED' }", s)
        self.assertIn("if ($data.filtered -and $auth) {", s)
        self.assertIn("($auth -or [int]$data.totalRows -le 25)", s)
        self.assertIn('PUBLIC_NO_LOAD_MORE_BUTTON_MAX_25_OFFERS', s)
        self.assertIn("if([string]$health.status -ne 'AVAILABLE'){", launcher)
        self.assertNotIn('"-RequireLogin")', launcher)
        self.assertIn("if($diag.status -eq 'BLOCKED'){Note 'CHALLENGE_STILL_PRESENT';return}", watchdog)
        self.assertIn("if(!$browserNeedsBootstrap -and $diag.status -ne 'AVAILABLE')", watchdog)
        self.assertNotIn("'LOGIN_REQUIRED' {20;break}", watchdog)
        self.assertNotIn("'LOGIN_REQUIRED' {20;break}", launcher)

    def test_catalog_direct_id_does_not_abort_on_transient_challenge(self):
        s = P.read_text(encoding="utf-8-sig")
        self.assertIn("$lookupDeadline=[DateTime]::UtcNow.AddSeconds($ChallengeWaitSeconds+10)", s)
        self.assertIn("for($attempt=0;($attempt -lt 18 -or $challengeSeen) -and", s)
        self.assertIn("CARDMARKET_DIRECT_ID_CHALLENGE_WAITING: no further provider requests", s)
        self.assertIn("CARDMARKET_DIRECT_ID_CHALLENGE_CLEARED: resuming current browser page", s)
        self.assertIn("if($challengeSeen){$challenged=$true}", s)
        start = s.index("if(!$savedUrl -and !$catalogIdLookupUnsupported")
        end = s.index("if ($savedUrl) {", start)
        block = s[start:end]
        self.assertEqual(block.count("Send-Cdp 'Page.navigate'"), 1)

    def test_candidate_lookup_keeps_shadowless_as_unverified_special(self):
        m = load_resolver()
        guard = {"base1": "Base-Set", "sv01": "Scarlet-Violet"}
        en_link = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Kadabra-V1-BS32"
        base = {
            "cardyssey_karte": "base1-32",
            "variante_id": "variant-a",
            "set_id": "base1",
            "kartennummer": "32",
            "drucktyp": "normal",
            "sonderdruck": "shadowless",
            "foil": "",
            "stempel": '["1st-edition"]',
            "routing_state": "UNVERIFIED",
            "reference_print_verified": "NO",
            "reference_product_url": "",
            "known_url": "",
            "needs_price": "NO",
            "existing_price_eur": "2.00",
            "manual_scan_requested_at": "",
        }
        candidate = {
            "key": "base1-32|variant-a",
            "status": "OFFLINE_UNIQUE_V1_PAGE_CANDIDATE",
            "reference_product_url_candidate": en_link,
        }
        result, counts = m.build_updates([base], [candidate], guard, "en", "2026-11-13T12:00:00Z")
        self.assertEqual(counts["new_hints"], 1)
        self.assertEqual(result[0]["reference_product_url"], en_link)
        self.assertEqual(result[0]["reference_print_verified"], "NO")
        self.assertEqual(result[0]["reference_standard_filter_supported"], "NO")
        self.assertEqual(result[0]["needs_price"], base["needs_price"])
        self.assertEqual(result[0]["existing_price_eur"], base["existing_price_eur"])

    def test_holo_reverse_can_use_standard_filter_but_never_auto_price(self):
        m = load_resolver()
        guard = {"sv01": "Scarlet-Violet"}
        url = "https://www.cardmarket.com/de/Pokemon/Products/Singles/Scarlet-Violet/Meowscarada-V1-SVI015"
        r = {
            "cardyssey_karte": "sv01-015", "variante_id": "reverse",
            "set_id": "sv01", "kartennummer": "15",
            "drucktyp": "Reverse", "sonderdruck": "", "foil": "",
            "stempel": "[]", "reference_product_url": "",
            "reference_print_verified": "NO", "routing_state": "UNVERIFIED",
            "known_url": "", "manual_scan_requested_at": "",
        }
        candidate = {"key": "sv01-015|reverse", "status": "OFFLINE_UNIQUE_V1_PAGE_CANDIDATE",
                     "reference_product_url_candidate": url}
        out, counts = m.build_updates([r], [candidate], guard, "de", "2026-11-13T12:00:00Z")
        self.assertEqual(out[0]["reference_standard_filter_supported"], "YES")
        self.assertEqual(out[0]["reference_print_verified"], "NO")
        self.assertEqual(counts["filter_supported"], 1)
        self.assertFalse(m.page_candidate(url.replace("-SVI015", "-SVI016"), "Scarlet-Violet", "de", "15"))
        self.assertFalse(m.page_candidate(url.replace("/Scarlet-Violet/", "/Additionals/"), "Scarlet-Violet", "de", "15"))

    def test_manual_verified_reference_is_not_overwritten(self):
        m = load_resolver()
        r = {"cardyssey_karte": "sv01-015", "variante_id": "normal",
             "set_id": "sv01", "kartennummer": "15",
             "drucktyp": "normal", "sonderdruck": "", "foil": "",
             "stempel": "[]", "reference_product_url": "https://other.example",
             "reference_print_verified": "YES", "routing_state": "VERIFIED_PRODUCT_ID",
             "known_url": "https://other.example", "manual_scan_requested_at": ""}
        candidate = {"key": "sv01-015|normal", "status": "OFFLINE_UNIQUE_V1_PAGE_CANDIDATE",
                     "reference_product_url_candidate": "https://www.cardmarket.com/de/Pokemon/Products/Singles/Scarlet-Violet/Meowscarada-V1-SVI015"}
        out, counts = m.build_updates([r], [candidate], {"sv01": "Scarlet-Violet"}, "de", "2026-11-13T12:00:00Z")
        self.assertEqual(out[0], r)
        self.assertEqual(counts["rejected_existing_reference"], 1)


if __name__ == "__main__":
    unittest.main()
