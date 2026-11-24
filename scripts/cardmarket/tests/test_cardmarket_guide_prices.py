import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'guide_prices', Path(__file__).resolve().parents[1] / 'core/publish-cardmarket-guide-prices.py')
gp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gp)

NOW = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)


def q(card, variant='v', **extra):
    row = {'cardyssey_karte': card, 'variante_id': variant, 'set_id': card.rsplit('-', 1)[0], 'drucktyp': 'Holo',
           'variant_class': 'STANDARD', 'index_status': 'DIRECT_PRODUCT_URL', 'index_product_id': '100',
           'index_product_url': 'https://www.cardmarket.com/de/Pokemon/Products/Singles/X/Y', 'stempel': '[]'}
    row.update(extra)
    return row


GUIDES = {100: {'trend': 12.5, 'avg30': 10, 'trend-holo': 3.2}, 200: {'avg30': 7.0}}


def run(rows, prices=None, routes=()):
    queue = {f"{r['cardyssey_karte']}|{r['variante_id']}": r for r in rows}
    return gp.plan(queue, GUIDES, prices or {}, set(routes), NOW)


class GuidePriceTests(unittest.TestCase):
    def test_exact_cardmarket_value_without_multiplier(self):
        updates, _, stats = run([q('a-1'), q('a-2', drucktyp='Reverse'),
                                 q('a-3', index_product_id='200')])
        self.assertEqual([u['price'] for u in updates], [12.5, 3.2, 7.0])
        self.assertEqual([u['key'] for u in updates], ['trend', 'trend-holo', 'avg30'])
        self.assertEqual(stats['publish'], 3)
        self.assertFalse(hasattr(gp, 'language_factors'))

    def test_only_own_verified_ids(self):
        updates, _, stats = run([q('a-1', index_status='SET_NOT_INDEXED'),
                                 q('a-2', index_status='GUIDE_PRICE_BELOW_THRESHOLD', index_match='DIRECT_PRODUCT_URL'),
                                 q('a-3', index_status='REVIEW_GROUP')])
        self.assertEqual([u['card'] for u in updates], ['a-2'])
        self.assertEqual(stats['no_verified_product_id'], 2)

    def test_keeps_fresh_browser_prices_routes_and_skips_mixed_prints(self):
        prices = {'a-1|v': {'source': 'CARDMARKET_DE_NM_WEB', 'updated': '2026-11-20T00:00:00+00:00', 'eur': 50},
                  'a-2|v': {'source': 'CARDMARKET_DE_NM_WEB', 'updated': '2026-09-01T00:00:00+00:00', 'eur': 50},
                  'a-4|v': {'source': 'CARDTRADER_MARKETPLACE', 'eur': 9}}
        rows = [q('a-1'), q('a-2'), q('a-3'), q('a-4'), q('a-5', variant_class='SPECIAL_UNIQUE_FILTER'),
                q('b-1'), q('b-1', 'first', variant_class='FIRST_EDITION')]
        updates, protect, stats = run(rows, prices, routes={'a-3|v'})
        self.assertEqual([u['card'] for u in updates], ['a-2'])
        self.assertEqual(protect, ['a-1|v'])
        # b-1 plain is skipped because its card has a 1st edition print.
        self.assertEqual(stats['first_edition_mixed_in_guide'], 1)
        self.assertEqual(stats['special_print_not_in_guide'], 2)


if __name__ == '__main__':
    unittest.main()
