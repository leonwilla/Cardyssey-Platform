import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'guide_prices', Path(__file__).resolve().parents[1] / 'core/publish-cardmarket-guide-prices.py')
gp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gp)

NOW = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)


def q(card, variant='v', pid='100', **extra):
    row = {'cardyssey_karte': card, 'variante_id': variant, 'set_id': card.rsplit('-', 1)[0], 'drucktyp': 'Holo',
           'variant_class': 'STANDARD', 'index_status': 'DIRECT_PRODUCT_URL', 'index_product_id': pid,
           'index_product_url': 'https://www.cardmarket.com/de/Pokemon/Products/Singles/X/Y', 'stempel': '[]'}
    row.update(extra)
    return row


GUIDES = {100: {'trend': 12.5, 'avg30': 10, 'trend-holo': 3.2}, 200: {'avg30': 7.0}, 300: {'trend': 1.0}}


def run(rows, prices=None):
    queue = {f"{r['cardyssey_karte']}|{r['variante_id']}": r for r in rows}
    return gp.plan(queue, GUIDES, prices or {}, NOW)


class GuidePriceTests(unittest.TestCase):
    def test_exact_cardmarket_value_without_multiplier(self):
        updates, _, stats = run([q('a-1'), q('a-2', drucktyp='Reverse'), q('a-3', pid='200')])
        self.assertEqual([u['price'] for u in updates], [12.5, 3.2, 7.0])
        self.assertEqual([u['key'] for u in updates], ['trend', 'trend-holo', 'avg30'])
        self.assertEqual(stats['publish'], 3)

    def test_only_own_verified_ids(self):
        updates, _, stats = run([q('a-1', index_status='SET_NOT_INDEXED'),
                                 q('a-2', index_status='GUIDE_PRICE_BELOW_THRESHOLD', index_match='DIRECT_PRODUCT_URL'),
                                 q('a-3', index_status='REVIEW_GROUP'),
                                 q('a-4', index_status='HUMAN_ROUTE_KEPT', routing_state='VERIFIED_PRODUCT_ID',
                                   catalog_singleton_id='300')])
        self.assertEqual([u['card'] for u in updates], ['a-2', 'a-4'])
        self.assertEqual(stats['no_verified_product_id'], 2)

    def test_collision_plain_and_unique_specials_are_published(self):
        updates, _, _ = run([q('a-1', variant_class='COLLISION_PLAIN'),
                             q('a-2', variant_class='SPECIAL_UNIQUE_FILTER', drucktyp='Reverse')])
        self.assertEqual(len(updates), 2)

    def test_ambiguous_guide_is_skipped(self):
        rows = [q('b-1'), q('b-1', 'first', variant_class='FIRST_EDITION', stempel='["1. Auflage"]'),
                q('c-1', 'normal'), q('c-1', 'stamp', routing_state='VERIFIED_PRODUCT_ID',
                                      index_status='HUMAN_ROUTE_KEPT', catalog_singleton_id='100')]
        updates, _, stats = run(rows)
        self.assertEqual(updates, [])
        self.assertEqual(stats['first_edition_browser_only'], 2)
        self.assertEqual(stats['variants_share_one_product'], 2)

    def test_keeps_fresh_browser_and_manual_prices(self):
        prices = {'a-1|v': {'source': 'CARDMARKET_DE_NM_WEB', 'updated': '2026-11-20T00:00:00+00:00', 'eur': 50},
                  'a-2|v': {'source': 'CARDMARKET_DE_NM_WEB', 'updated': '2026-09-01T00:00:00+00:00', 'eur': 50},
                  'a-3|v': {'source': 'MANUAL_ADMIN', 'eur': 9},
                  'a-4|v': {'source': 'TCGCSV_TCGPLAYER', 'eur': 9}}
        updates, keep, stats = run([q('a-1'), q('a-2'), q('a-3'), q('a-4')], prices)
        self.assertEqual([u['card'] for u in updates], ['a-2', 'a-4'])
        self.assertEqual(keep, ['a-1|v'])
        self.assertEqual(stats['keep_manual'], 1)

    def test_cleanup_sql_keeps_only_cardmarket_and_blocks_api_worker(self):
        self.assertIn("NOT (COALESCE(source,'') = ANY(ARRAY[{cardmarket}]))", gp.CLEAN)
        self.assertIn('next_attempt_at={never}', gp.CLEAN)
        self.assertNotIn('TCGDEX', ''.join(gp.CARDMARKET))
        self.assertNotIn('POKEMONTCGIO_CARDMARKET', gp.CARDMARKET)


class RobustTrendTests(unittest.TestCase):
    def test_normal_trend_is_kept(self):
        self.assertEqual(gp.guide_value({'trend': 10.0, 'avg30': 12.0, 'avg7': 9.0}, False), (10.0, 'trend'))

    def test_broken_low_trend_uses_median(self):
        value, key = gp.guide_value({'trend': 0.02, 'avg30': 1047.94, 'avg7': 422.43}, False)
        self.assertEqual(value, 422.43)
        self.assertTrue(key.startswith('avg7'))

    def test_broken_high_trend_uses_median(self):
        value, _ = gp.guide_value({'trend': 295.69, 'avg30': 48.02, 'avg7': 150.95}, False)
        self.assertEqual(value, 150.95)

    def test_only_avg30_reference(self):
        value, key = gp.guide_value({'trend-holo': 0.02, 'avg30-holo': 12.0}, True)
        self.assertEqual((value, key), (12.0, 'avg30-holo (Trend unplausibel)'))


if __name__ == '__main__':
    unittest.main()
