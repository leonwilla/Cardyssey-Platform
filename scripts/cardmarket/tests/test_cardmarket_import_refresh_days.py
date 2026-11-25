import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'core/import-cardmarket-browser-observations.py'
spec = importlib.util.spec_from_file_location('cm_import', PATH)
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)


class ImportRefreshDaysTests(unittest.TestCase):
    def test_same_tiers_as_collector(self):
        f = cm.refresh_days_for
        self.assertEqual(f({'existing_price_eur': '300'}, None), 1)
        self.assertEqual(f({'existing_price_eur': '120.5'}, None), 7)
        self.assertEqual(f({'existing_price_eur': '25'}, 400.0), 28)  # queue price wins
        self.assertEqual(f({'existing_price_eur': '', 'needs_price': 'YES'}, 260.0), 1)  # scan median as fallback
        self.assertEqual(f({'existing_price_eur': '', 'needs_price': 'YES'}, None), 7)

    def test_offer_ceiling_matches_collector_cap(self):
        self.assertEqual(cm.MAX_OFFERS, 1200)


if __name__ == '__main__':
    unittest.main()
