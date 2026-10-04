#!/usr/bin/env python3
"""Unit tests for the conservative regional image fallback matcher."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).with_name("sync-pokemontcgapi-images.py")
SPEC = importlib.util.spec_from_file_location("fallback", SCRIPT)
fallback = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fallback)


class MatchingTests(unittest.TestCase):
    def test_number_normalizes_fraction_and_zero_padding(self):
        self.assertEqual(fallback.number("001/100"), "1")
        self.assertEqual(fallback.number("001"), "1")
        self.assertEqual(fallback.number("TG01/TG30"), "TG01")

    def test_set_code_match_wins(self):
        local = {"set_id": "SV8a", "set_name": "Different display name"}
        remote = [
            {"id": "sv8a", "code": "SV8A", "name": "Remote"},
            {"id": "other", "code": "OTHER", "name": "Different display name"},
        ]
        self.assertEqual(fallback.set_candidates(local, remote), [remote[0]])

    def test_exact_normalized_set_name_fallback(self):
        local = {"set_id": "legacy-local", "set_name": "Expansion Pack"}
        remote = [{"id": "jp-exp", "code": "EXP", "name": "Expansion Pack"}]
        self.assertEqual(fallback.set_candidates(local, remote), remote)

    def test_ambiguous_set_name_is_rejected(self):
        local = {"set_id": "unknown", "set_name": "Promo"}
        remote = [
            {"id": "one", "code": "ONE", "name": "Promo"},
            {"id": "two", "code": "TWO", "name": "Promo"},
        ]
        self.assertEqual(fallback.set_candidates(local, remote), [])

    def test_only_expected_image_host_is_accepted(self):
        good = "https://img.pokemontcgapi.com/media/cards/x/1-normal.webp?sig=x"
        self.assertEqual(fallback.verified_image(good), good)
        with self.assertRaises(ValueError):
            fallback.verified_image("https://example.com/card.webp")


if __name__ == "__main__":
    unittest.main()
