import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ebay_sold_import as si  # noqa: E402

TODAY = date(2026, 11, 26)


class SoldImportTests(unittest.TestCase):
    def test_parse_sold_row(self):
        item = {"title": "Evoli 074/131 Deutsch Wird in neuem Fenster oder Tab geöffnet",
                "url": "https://www.ebay.de/itm/123456789012",
                "text": "Verkauft 25. Nov 2026 Evoli 074/131 Deutsch Gebraucht | Privat EUR 2,50 Sofort-Kaufen +EUR 1,60 Versand"}
        self.assertEqual(si.parse_item(item, TODAY),
                         ("Evoli 074/131 Deutsch", 2.5, date(2026, 11, 25), "123456789012",
                          "https://www.ebay.de/itm/123456789012"))
        self.assertIsNone(si.parse_item(dict(item, text=item["text"].replace("EUR 2,50", "EUR 2,31 bis EUR 3,50")), TODAY))
        self.assertIsNone(si.parse_item(dict(item, text="Verkauft 3. Mär 2027 EUR 1,00"), TODAY))

    def test_window_grows_and_links_only_30_days(self):
        def sale(days, eur):
            return (TODAY - timedelta(days=days), eur, "t", "https://www.ebay.de/itm/1", "1")
        v = si.value_for([sale(5, 10), sale(10, 12), sale(20, 14), sale(200, 99)], TODAY)
        self.assertEqual((v["median"], v["days"], v["n"]), (12, 30, 3))
        v = si.value_for([sale(5, 10), sale(45, 12), sale(80, 14)], TODAY)
        self.assertEqual((v["days"], v["label"]), (90, "90 Tage"))
        self.assertEqual([r["url"] is not None for r in v["recent"]], [True, False, False])
        self.assertIsNone(si.value_for([sale(5, 10), sale(400, 12)], TODAY))


if __name__ == "__main__":
    unittest.main()
