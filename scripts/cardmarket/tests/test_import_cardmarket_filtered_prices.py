
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

s=importlib.util.spec_from_file_location('cmprice',source_path('import-cardmarket-filtered-prices.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


class FilteredImportTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.observations = self.directory / "observations.jsonl"
        self.now = datetime.now(timezone.utc)
        self.observation = {
            "language": "de", "card_id": "sv04.5-013", "variant_id": "reverse",
            "set_id": "sv04.5", "number": "013", "product_id": "751539",
            "url": "https://www.cardmarket.com/de/Pokemon/Products/Singles/Paldean-Fates/Heat-Rotom-PAF013",
            "identity_confirmed": True, "card_number_url_verified": True,
            "status": "FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE", "all_pages_complete": False,
            "offer_pages_attempted": 3, "pagination_failure": "MORE_OFFERS_STILL_VISIBLE",
            "verified_lang_nm_offers": 20, "offers_seen": 20, "sample_median_eur": 1.25,
            "filter_mode": "CANONICAL_URL_DOM_VERIFIED", "access_mode": "AUTHENTICATED",
            "expected_reverse_holo": "Y", "expected_first_edition": "0",
            "exact_print_filter_supported": False, "seen_at": self.now.isoformat(),
        }
        self.queue_row = {
            "cardyssey_karte": "sv04.5-013", "variante_id": "reverse", "set_id": "sv04.5",
            "kartennummer": "013", "catalog_singleton_id": "751539", "catalog_expansion_id": "5546",
            "drucktyp": "Reverse", "foil": "", "stempel": "[]", "sonderdruck": "",
            "candidate_status": "SINGLE_SET_PRODUCT",
        }
        self.guards = self.directory / "verified-set-url-guards.json"
        self.guards.write_text(json.dumps({"sv04.5": "Paldean-Fates"}), encoding="utf-8")

    def write_queue(self, language, **changes):
        row = {**self.queue_row, **changes}
        with (self.directory / f"queue-{language}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)

    def collect(self, scan_language="de", **changes):
        row = {**self.observation, **changes}
        self.observations.write_text(json.dumps(row) + "\n", encoding="utf-8")
        return m.collect(self.observations, scan_language, self.now)

    def test_standard_at_paging_limit_can_publish_for_each_language(self):
        for language in ("de", "en"):
            with self.subTest(language=language):
                self.write_queue(language)
                rows = self.collect(language, **{
                    "language": language, "url": self.observation["url"].replace("/de/", f"/{language}/"),
                })
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["language"], language)
                self.assertEqual(rows[0]["price"], 1.25)
                self.assertTrue(rows[0]["automatic_standard"])
                self.assertTrue(rows[0]["page_limited_sample"])

    def test_complete_standard_uses_the_complete_median(self):
        self.write_queue("de")
        rows = self.collect(
            status="COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED", all_pages_complete=True,
            median_all_offers_eur=2.0, verified_lang_nm_offers=5, offers_seen=5,
            pagination_failure="",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["price"], 2.0)
        self.assertTrue(rows[0]["automatic_standard"])
        self.assertFalse(rows[0]["page_limited_sample"])

    def test_cheapest_five_median_is_preferred_over_all_offer_median(self):
        self.write_queue("de")
        rows = self.collect(
            status="COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED", all_pages_complete=True,
            median_all_offers_eur=9.0, entry_five_median_eur=2.5, verified_lang_nm_offers=5,
            offers_seen=5, pagination_failure="",
        )
        self.assertEqual(rows[0]["price"], 2.5)

    def test_invalid_cheapest_five_falls_back_to_median(self):
        self.write_queue("de")
        for bad in (None, True, 0, float("nan")):
            with self.subTest(bad=bad):
                rows = self.collect(
                    status="COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED", all_pages_complete=True,
                    median_all_offers_eur=2.0, entry_five_median_eur=bad, verified_lang_nm_offers=5,
                    offers_seen=5, pagination_failure="",
                )
                self.assertEqual(rows[0]["price"], 2.0)

    def test_sample_requires_at_least_twenty_valid_offers_and_actual_page_limit(self):
        self.write_queue("de")
        for changes in (
            {"offers_seen": 19, "verified_lang_nm_offers": 19},
            {"verified_lang_nm_offers": 19}, {"offers_seen": 21},
            {"offer_pages_attempted": 2}, {"access_mode": "PUBLIC_LIMITED"},
            {"pagination_failure": "LOAD_MORE_DISABLED_OR_LIMIT_REACHED"},
            {"pagination_failure": "DUPLICATE_OR_MISSING_OFFER_ID"},
            {"pagination_failure": "DEFERRED_LOGIN_REQUIRED"},
            {"status": "FILTER_NOT_APPLIED"},
            {"sample_median_eur": True}, {"sample_median_eur": float("nan")},
            {"sample_median_eur": 0},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(self.collect(**changes), [])

    def test_sample_requires_live_identity_number_and_filter_evidence(self):
        self.write_queue("de")
        for changes in (
            {"identity_confirmed": False}, {"card_number_url_verified": False},
            {"number": "023"}, {"product_id": "751549"}, {"set_id": "sv04"},
            {"filter_mode": None}, {"expected_reverse_holo": "N"}, {"expected_first_edition": "Y"},
            {"language": "en"}, {"seen_at": (self.now - timedelta(days=9)).isoformat()},
            {"url": self.observation["url"].replace("Paldean-Fates", "Paradox-Rift")},
            {"url": self.observation["url"] + "?language=1&minCondition=2&isReverseHolo=Y"},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(self.collect(**changes), [])

    def test_sample_requires_a_verified_set_and_a_unique_catalog_product(self):
        self.write_queue("de", catalog_singleton_id="751539,751549")
        self.assertEqual(self.collect(), [])
        self.write_queue("de", catalog_expansion_id="")
        self.assertEqual(self.collect(), [])
        self.write_queue("de", candidate_status="SET_EXPANSION_AMBIGUOUS")
        self.assertEqual(self.collect(), [])
        self.write_queue("de")
        self.guards.unlink()
        self.assertEqual(self.collect(), [])

    def test_special_prints_and_versioned_products_are_excluded(self):
        for changes in (
            {"foil": "Pokéball"}, {"foil": "Meisterball"},
            {"stempel": '["Pokémon Center"]'}, {"sonderdruck": "V2"},
        ):
            with self.subTest(changes=changes):
                self.write_queue("de", **changes)
                self.assertEqual(self.collect(), [])
        self.write_queue("de")
        self.assertEqual(self.collect(observed_url_version="V1"), [])
        for marker in ("V2", "%56%32"):
            url = self.observation["url"].replace("-PAF013", f"-{marker}-PAF013")
            self.assertEqual(self.collect(url=url), [])

    def test_first_edition_in_either_language_requires_an_explicit_edition_filter(self):
        self.write_queue("de")
        self.write_queue("en", stempel='["1st Edition"]')
        self.assertEqual(self.collect(), [])
        self.assertEqual(len(self.collect(expected_first_edition="N", exact_print_filter_supported=True)), 1)

    def test_complete_special_keeps_human_route_and_explicit_filter_requirements(self):
        self.write_queue("de", sonderdruck="unlimited")
        url = self.observation["url"].replace("-PAF013", "-V1-PAF013")
        full = {
            "status": "COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED", "all_pages_complete": True,
            "median_all_offers_eur": 1.25, "expected_first_edition": "N",
            "exact_print_filter_supported": True,
            "url": url + "?language=3&minCondition=2&isReverseHolo=Y&isFirstEd=N",
        }
        rows = self.collect(**full)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["automatic_standard"])
        full["url"] = full["url"].split("&isFirstEd")[0]
        self.assertEqual(self.collect(**full), [])
        full["url"] += "&isFirstEd=N"
        full["non_filterable_print_attributes"] = ["foil:Pokéball"]
        self.assertEqual(self.collect(**full), [])

    def test_combined_observations_keep_independent_language_prices(self):
        evidence = {
            "filter_mode": "COMBINED_URL_DOM_VERIFIED",
            "source_filter_language_ids": "1,3",
            "combined_product_id_verified": "751539", "combined_offers_seen": 50,
            "source_product_url": self.observation["url"],
        }
        for language, price in (("de", 1.25), ("en", 2.50)):
            self.write_queue(language)
            rows = self.collect(language, **{
                **evidence, "language": language, "sample_median_eur": price,
                "url": self.observation["url"].replace("/de/", f"/{language}/"),
            })
            self.assertEqual([(r["language"], r["price"]) for r in rows], [(language, price)])
        for bad in (
            {"source_filter_language_ids": "1"}, {"combined_product_id_verified": "999999"},
            {"combined_offers_seen": 19}, {"combined_offers_seen": None},
            {"source_product_url": "https://evil.example/de/Pokemon/Products/Singles/Paldean-Fates/Heat-Rotom-PAF013"},
            {"source_product_url": self.observation["url"].replace("PAF013", "PAF014")},
            {"status": "SINGLE_LANGUAGE_FALLBACK_REQUIRED"},
        ):
            with self.subTest(bad=bad):
                self.assertEqual(self.collect(**{**evidence, **bad}), [])
        for special in ({"foil": "Pokéball"}, {"stempel": '["staff"]'}, {"sonderdruck": "shadowless"}):
            self.write_queue("de", **special)
            self.assertEqual(self.collect(**evidence), [])

    def test_sql_protects_human_routes_and_preserves_single_cache_price(self):
        self.assertIn("verification_state='VERIFIED_PRODUCT_ID' AND matches_route AND source_evidence LIKE 'Human confirmed exact%'", m.SQL)
        self.assertIn("automatic_standard AND (verification_state IS DISTINCT FROM 'VERIFIED_PRODUCT_ID' OR matches_route)", m.SQL)
        self.assertIn("INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,", m.SQL)
        self.assertIn("COALESCE(cached.legacy_variant, print.legacy_variant)", m.SQL)
        self.assertIn("ON CONFLICT(card_id,language_code,variant_id) DO UPDATE", m.SQL)


if __name__ == "__main__":
    unittest.main()
