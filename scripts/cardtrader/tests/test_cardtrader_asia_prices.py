import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cardtrader_asia_prices as ct  # noqa: E402


class AsiaPriceTests(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(ct.number_key("109"), ("", 109))
        self.assertEqual(ct.number_key("009/101"), ("", 9))
        self.assertEqual(ct.number_key("SV030"), ("SV", 30))

    def test_variant_kinds(self):
        self.assertEqual(ct.variant_kind({"type": "normal"}), ("main", False, False))
        self.assertEqual(ct.variant_kind({"type": "reverse", "foil": "masterball"}), ("masterball", True, False))
        self.assertEqual(ct.variant_kind({"type": "normal", "stamps": ["1st edition"]}), ("main", False, True))
        self.assertIsNone(ct.variant_kind({"type": "holo", "stamps": ["staff"]}))
        self.assertIsNone(ct.variant_kind({"type": "holo", "foil": "cosmos"}))

    def test_price(self):
        self.assertIsNone(ct.price_from([{"eur": 3.0}]))
        self.assertEqual(ct.price_from([{"eur": p} for p in (1, 2, 3, 4, 5, 90)]), 3)

    def test_pattern_expansions(self):
        exps = [{"code": "sv8a", "name": "Terastal Festival ex"},
                {"code": "p-sv8a", "name": "Terastal Festival ex - Poké Ball Reverse Holo"},
                {"code": "sv2a", "name": "Pokémon Card 151"},
                {"code": "151pkmr", "name": "Pokémon Card 151 - Master Ball Reverse Holo"}]
        p = ct.pattern_expansions(exps)
        self.assertEqual(p["sv8a"]["pokeball"]["code"], "p-sv8a")
        self.assertEqual(p["sv2a"]["masterball"]["code"], "151pkmr")


if __name__ == "__main__":
    unittest.main()
