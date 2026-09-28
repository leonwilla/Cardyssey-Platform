import importlib.util
from pathlib import Path
import unittest

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


if __name__ == "__main__":
    unittest.main()
