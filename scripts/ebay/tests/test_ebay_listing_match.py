import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ebay_listing_match as em  # noqa: E402

NORMAL = {"type": "Normal", "stamps": []}
REVERSE = {"type": "Reverse", "stamps": []}
POKEBALL = {"type": "Reverse", "foil": "Pokéball", "stamps": []}
MASTERBALL = {"type": "Reverse", "foil": "Meisterball", "stamps": []}
EEVEE = [NORMAL, REVERSE, POKEBALL, MASTERBALL]


def ok(title, variant, language="de", names=("Evoli", "Eevee"), number="074", total=131):
    spec, status = em.variant_spec(variant, [v for v in EEVEE if v is not variant])
    return em.matches(title, language=language, names=list(names), number=number, total=total,
                      set_words=["prismatische"], spec=spec)


class MatchTests(unittest.TestCase):
    def test_variants_are_separated(self):
        t = "Pokémon Evoli 074/131 Meisterball Reverse Holo Deutsch"
        self.assertTrue(ok(t, MASTERBALL))
        self.assertFalse(ok(t, POKEBALL))
        self.assertFalse(ok(t, REVERSE))
        self.assertFalse(ok(t, NORMAL))
        self.assertTrue(ok("Pokemon Evoli PRE 074/131 DEUTSCH Reverse Holo", REVERSE))
        self.assertTrue(ok("Pokemon Evoli 074/131 Prismatische Entwicklungen Deutsch", NORMAL))

    def test_language_number_and_junk(self):
        self.assertFalse(ok("Pokemon Evoli 074/131 English", NORMAL))
        self.assertFalse(ok("Pokemon Evoli 075/131 Deutsch", NORMAL))
        self.assertFalse(ok("Evoli 074/131 Deutsch PSA 10", NORMAL))
        self.assertFalse(ok("Evoli 074/131 Deutsch Fanartikel Metall", NORMAL))
        self.assertFalse(ok("Evoli 074/131 Deutsch Fehldruck", NORMAL))
        # German name alone proves the language
        self.assertTrue(ok("Pokemon Evoli 074/131 Prismatische", NORMAL))
        self.assertFalse(ok("Pokemon Eevee 074/131 Prismatic", NORMAL))

    def test_world_championship_and_uncertain(self):
        self.assertEqual(em.variant_spec({"type": "Normal", "stamps": ["jason-klaczynski"]}, [])[1], "SKIP")
        self.assertEqual(em.variant_spec({"type": "Normal", "stamps": ["Set-Logo"]}, [])[1], "UNCERTAIN")
        self.assertEqual(em.variant_spec({"type": "Holo", "subtype": "Fehlendes Erweiterungssymbol"}, [])[1],
                         "UNCERTAIN")
        self.assertEqual(em.variant_spec({"type": "Normal", "stamps": ["1. Auflage"]}, [])[0]["require"], ["first"])


if __name__ == "__main__":
    unittest.main()
