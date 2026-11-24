import csv
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


mon = load('admin/cardmarket_index_monitor.py', 'index_monitor')
fail = load('admin/cardmarket-live-failures.py', 'live_failures_idx')


def queue(base, lang, rows):
    cols = sorted({k for r in rows for k in r})
    with (base / f'queue-{lang}.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


class MonitorTests(unittest.TestCase):
    def test_speed_counts_only_full_hours_after_switch(self):
        now = datetime(2026, 11, 24, 13, 30, tzinfo=timezone.utc)
        obs = [{'seen_at': '2026-11-24T09:30:00Z', 'status': 'COMPLETE_FILTERED', 'product_load_mode': 'X'}]
        obs += [{'seen_at': f'2026-11-24T11:{m:02d}:00Z', 'status': 'COMPLETE_FILTERED', 'product_load_mode': 'X',
                 'lookup_strategy': 'EXPANSION_INDEX_DIRECT_V1'} for m in range(50)]
        obs += [{'seen_at': '2026-11-24T12:10:00Z', 'status': 'BLOCKED'}]
        obs += [{'seen_at': '2026-11-24T13:05:00Z', 'status': 'COMPLETE_FILTERED', 'product_load_mode': 'X'}]
        s = mon.speed(obs, now)
        self.assertEqual(s['pricesPerHour'], 16.7)  # hours 10, 11, 12 -> 50 / 3
        self.assertEqual(s['blocks'], 1)
        self.assertNotIn('2026-11-24T09:00Z', [h['hour'] for h in s['hours']])

    def test_backlog_separates_rescans(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            url = 'https://www.cardmarket.com/de/Pokemon/Products/Singles/Skyridge/Staryu-SK103'
            queue(base, 'de', [
                {'cardyssey_karte': 'a-1', 'variante_id': 'v', 'index_status': 'DIRECT_PRODUCT_URL', 'index_product_url': url},
                {'cardyssey_karte': 'a-2', 'variante_id': 'v', 'index_status': 'DIRECT_PRODUCT_URL_ID_CORRECTED', 'index_product_url': url},
                {'cardyssey_karte': 'a-3', 'variante_id': 'v', 'index_status': 'DIRECT_PRODUCT_URL', 'index_product_url': url},
                {'cardyssey_karte': 'a-4', 'variante_id': 'v', 'index_status': 'GUIDE_PRICE_BELOW_THRESHOLD', 'index_product_url': ''}])
            lines = [{'key': 'a-1|v', 'status': 'NO_EXACT_NUMBER_SEARCH_HIT', 'url': ''},
                     {'key': 'a-2|v', 'status': 'COMPLETE_FILTERED', 'url': url.replace('SK103', 'SK104')}]
            (base / 'browser-observations-de.jsonl').write_text('\n'.join(json.dumps(x) for x in lines))
            mon.CACHE = base / 'cache.json'
            b = mon.backlog(base, max_age=0)['de']
            self.assertEqual((b['rescanFailed'], b['rescanCorrected'], b['neverScanned']), (1, 1, 1))
            self.assertEqual(b['status:GUIDE_PRICE_BELOW_THRESHOLD'], 1)


class FailureListTests(unittest.TestCase):
    def test_cards_below_two_euro_leave_the_review_list(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            rows = [{'cardyssey_karte': c, 'variante_id': 'v', 'set_id': 'a', 'kartenname_suche': c,
                     'index_status': st, 'index_review_group': grp}
                    for c, st, grp in (('a-1', 'GUIDE_PRICE_BELOW_THRESHOLD', ''), ('a-2', 'REVIEW_GROUP', 'a|masterball'))]
            queue(base, 'de', rows)
            now = datetime.now(timezone.utc).isoformat()
            obs = [{'card_id': c, 'variant_id': 'v', 'set_id': 'a', 'status': 'NO_EXACT_NUMBER_SEARCH_HIT', 'seen_at': now}
                   for c in ('a-1', 'a-2')]
            (base / 'browser-observations-de.jsonl').write_text('\n'.join(json.dumps(x) for x in obs))
            r = fail.list_failures(base=base, language='de', kind='alle', decisions={}, for_export=True)
            self.assertEqual([x['cardId'] for x in r['items']], ['a-2'])
            self.assertEqual(r['guidePricedBelowThreshold'], 1)
            self.assertEqual(r['items'][0]['reviewGroup'], 'a|masterball')


class RescanWiringTests(unittest.TestCase):
    def test_index_upgrade_is_prioritised_and_not_marked_processed(self):
        policy = (ROOT / 'core/Cardmarket-Backoff-Policy.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('function Test-CardmarketIndexUpgradeDue', policy)
        self.assertIn('$priority.ToArray() + $corrected.ToArray() + $upgrade.ToArray() + $fresh.ToArray()', policy)
        self.assertLess(policy.index('Test-CardmarketIndexUpgradeDue $item $prior'),
                        policy.index('Test-CardmarketUnresolvedObservation $prior $Epoch){'))
        collector = (ROOT / 'core/cardmarket-language-browser-collector.ps1').read_text(encoding='utf-8-sig')
        self.assertEqual(collector.count('-not $indexUpgrade -and'), 2)


if __name__ == '__main__':
    unittest.main()
