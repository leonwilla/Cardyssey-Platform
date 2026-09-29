import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
import time
import urllib.error
import tempfile

spec = importlib.util.spec_from_file_location("catalog_sync", Path(__file__).with_name("sync-supplemental-catalog.py"))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SourceIdentityTests(unittest.TestCase):
    def sample(self):
        return {
            "url": "https://pokemoncard.co.kr/cards/detail/BS2025010013",
            "name": "다태우지네",
            "img": "https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/M1S/M1S_013.png",
            "set_name": "M1S", "number": "013", "set_total": "063", "pokedex_number": 851,
        }

    def test_korean_test_card_keeps_print_identity_and_unknown_variants(self):
        item = sync.record(self.sample(), "ko", "revision", {"851": "Infernopod"})
        self.assertEqual(item["details"]["localId"], "013")
        self.assertEqual(item["details"]["officialCount"], 63)
        self.assertEqual(item["germanSpecies"], "Infernopod")
        self.assertEqual(item["details"]["variants"], [])
        self.assertNotIn("tcgDexEur", item["details"])

    def test_wrong_language_and_untrusted_image_are_rejected(self):
        for language, image in [
            ("ja", self.sample()["img"]),
            ("ko", "https://example.org/card.png"),
            ("ko", "http://127.0.0.1/card.png"),
        ]:
            with self.subTest(language=language, image=image), self.assertRaises(ValueError):
                sync.record(dict(self.sample(), img=image), language, "revision", {})
        with self.assertRaises(ValueError):
            sync.official_url("https://asia.pokemon-card.com/tw/card-img/tw1.png", "id")

    def test_source_identity_survives_name_or_image_correction(self):
        first = sync.record(self.sample(), "ko", "one", {})
        second = sync.record(dict(self.sample(), name="Corrected name"), "ko", "two", {})
        self.assertEqual(first["sourceId"], second["sourceId"])

    def test_same_number_different_art_is_not_silently_merged(self):
        a = sync.record(self.sample(), "ko", "one", {})
        b = sync.record(dict(self.sample(), url="https://pokemoncard.co.kr/cards/detail/OTHER",
                             img="https://cards.image.pokemonkorea.co.kr/data/another.png"), "ko", "one", {})
        self.assertTrue(all(not row["allowMatch"] for row in sync.avoid_ambiguous_matches([a, b])))

    def test_asia_uses_explicit_product_code_and_omits_evolution_marker(self):
        html = '''<h1 class="pageHeader cardDetail"><span class="evolveMarker">Basic</span>Exeggcute</h1>
            <div class="cardImage"><img src="/id/card-img/id00019647.png"></div>
            <span class="collectorNumber">001/130</span>
            <section class="expansionLinkColumn"><a href="/id/card-search/list/?expansionCodes=MA6">Celebration</a></section>'''
        raw = sync.parse_asia(html, "id", "https://asia.pokemon-card.com/id/card-search/detail/19647/")
        self.assertEqual((raw["name"], raw["set_name"], raw["number"], raw["set_total"]), ("Exeggcute", "MA6", "001", "130"))
        with self.assertRaises(ValueError):
            sync.parse_asia(html.replace("expansionCodes=MA6", "keyword=MA6"), "id", raw["url"])


    def test_official_energy_and_promo_numbers_need_no_denominator(self):
        html = '<h1 class="cardDetail">Energy</h1><div class="cardImage"><img src="/th/card-img/th1.png"></div><span class="collectorNumber">NUMBER</span><section class="expansionLinkColumn"><a href="?expansionCodes=S8a">Anniversary</a></section>'
        for number in ("WAT", "MET", "001/S-P", "013"):
            raw = sync.parse_asia(html.replace("NUMBER", number), "th", "https://asia.pokemon-card.com/th/card-search/detail/1719/")
            self.assertEqual((raw["number"], raw["set_total"]), (number, "0"))
            self.assertEqual(sync.record(raw, "th", "r", {})["details"]["localId"], number)
        for number in ("", "001 or 002", "001/084/099"):
            with self.assertRaises(ValueError):
                sync.parse_asia(html.replace("NUMBER", number), "th", "https://asia.pokemon-card.com/th/card-search/detail/1719/")

    def test_transient_502_is_retried_but_403_is_not(self):
        url = "https://asia.pokemon-card.com/id/card-search/list/"
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b"valid"
        with patch.object(sync.urllib.request, "urlopen", side_effect=[urllib.error.HTTPError(url, 502, "Bad Gateway", {}, None), response]) as opener, patch.object(sync.time, "sleep"):
            self.assertEqual(sync.Fetcher(time.monotonic() + 90, 0).get(url), "valid")
            self.assertEqual(opener.call_count, 2)
        with patch.object(sync.urllib.request, "urlopen", side_effect=urllib.error.HTTPError(url, 403, "Forbidden", {}, None)) as opener, patch.object(sync.time, "sleep"):
            with self.assertRaises(urllib.error.HTTPError):
                sync.Fetcher(time.monotonic() + 90, 0).get(url)
            self.assertEqual(opener.call_count, 1)

    def test_resume_starts_at_last_committed_page(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp)
            folder = cache / "id"
            folder.mkdir()
            sync.save_json(folder / "progress.json", {"page": 2, "count": 1, "rejected": 0, "seen": ["https://asia.pokemon-card.com/id/card-search/detail/1/"]})
            sync.save_json(folder / "2.json", {"name": "Card", "set_name": "MA6", "number": "002", "set_total": "130", "url": "https://asia.pokemon-card.com/id/card-search/detail/2/", "img": "https://asia.pokemon-card.com/id/card-img/id2.png"})
            fetcher = MagicMock()
            fetcher.get.return_value = '<a href="/id/card-search/detail/2/">Card</a>'
            with patch.object(sync, "import_rows") as imported:
                self.assertEqual(sync.asia_records("id", cache, fetcher, True), (2, 0))
            fetcher.get.assert_called_once_with("https://asia.pokemon-card.com/id/card-search/list/?pageNo=2")
            self.assertFalse((folder / "progress.json").exists())


if __name__ == "__main__":
    unittest.main()
