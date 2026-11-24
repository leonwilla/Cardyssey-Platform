import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / 'cardmarket/core'):
    sys.path.insert(0, str(p))
import cardmarket_expansion_index as idx  # noqa: E402


def row(card, number, kind='Normal', **extra):
    base = {'cardyssey_karte': card, 'variante_id': card + ':' + kind, 'set_id': card.rsplit('-', 1)[0],
            'kartennummer': number, 'drucktyp': kind, 'sonderdruck': '', 'foil': '', 'stempel': '[]',
            'needs_price': 'NO', 'existing_price_eur': '5.00', 'routing_state': 'SOURCE_ONLY',
            'catalog_singleton_id': '', 'catalog_expansion_id': '', 'cardmarket_ids': '', 'set_card_candidate_ids': ''}
    base.update(extra)
    return base


SKYRIDGE = {
    '275361': {'slug': 'Skyridge', 'product': 'Staryu-SK104', 'idExpansion': '1538'},
    '275362': {'slug': 'Skyridge', 'product': 'Staryu-SK103', 'idExpansion': '1538'},
    '275250': {'slug': 'Skyridge', 'product': 'Gengar-V2-SK10', 'idExpansion': '1538'},
    '275269': {'slug': 'Skyridge', 'product': 'Gyarados-V1-SKH10', 'idExpansion': '1538'},
    '275300': {'slug': 'Skyridge', 'product': 'Charizard-V1-SK146', 'idExpansion': '1538'},
    '275301': {'slug': 'Skyridge', 'product': 'Celebi-SK145', 'idExpansion': '1538'},
}
EXPANSIONS = {'1538': {'slug': 'Skyridge', 'slugVerified': True, 'crawledAt': '2026-11-24'}}
CATALOG = {int(k): {'idProduct': int(k), 'idExpansion': 1538} for k in SKYRIDGE}


def apply(rows, minimum=idx.MIN_BROWSER_SCAN_EUR, rules=None):
    return idx.apply_index(rows, 'de', SKYRIDGE, EXPANSIONS, {}, CATALOG, {'ecard3': 1538}, minimum=minimum,
                           rules=rules)


class VariantClassTests(unittest.TestCase):
    def test_classes(self):
        self.assertEqual(idx.variant_class(row('a-1', '1')), 'STANDARD')
        self.assertEqual(idx.variant_class(row('a-1', '1', 'Reverse')), 'STANDARD')
        self.assertEqual(idx.variant_class(row('a-1', '1', stempel='["1. Auflage"]')), 'FIRST_EDITION')
        self.assertEqual(idx.variant_class(row('a-1', '1', sonderdruck='unbegrenzt')), 'FIRST_EDITION')
        for extra in ({'foil': 'Meisterball'}, {'foil': 'cosmos'}, {'stempel': '["Set-Logo"]'},
                      {'stempel': '["1st-edition", "staff"]'}, {'sonderdruck': 'schattenlos'},
                      {'sonderdruck': 'Copyright 1999-2000'}):
            self.assertEqual(idx.variant_class(row('a-1', '1', **extra)), 'SPECIAL', extra)

    def test_threshold(self):
        self.assertFalse(idx.needs_browser_scan(row('a-1', '1', existing_price_eur='1.99')))
        self.assertTrue(idx.needs_browser_scan(row('a-1', '1', existing_price_eur='2.00')))
        self.assertTrue(idx.needs_browser_scan(row('a-1', '1', needs_price='YES', existing_price_eur='')))


class NumberTests(unittest.TestCase):
    def test_main_prefix_separates_holo_subset(self):
        self.assertTrue(idx.number_matches('Gengar-V2-SK10', '10', main_prefix='SK'))
        self.assertFalse(idx.number_matches('Gyarados-V1-SKH10', '10', main_prefix='SK'))
        self.assertTrue(idx.number_matches('Gyarados-V1-SKH10', 'H10', main_prefix='SK'))
        self.assertFalse(idx.number_matches('Gengar-V2-SK10', 'H10', main_prefix='SK'))

    def test_modern_and_subset_numbers(self):
        self.assertTrue(idx.number_matches('Crushing-Hammer-SVI168', '168', main_prefix='SVI'))
        self.assertTrue(idx.number_matches('Pikachu-SVI013', '013', main_prefix='SVI'))
        self.assertTrue(idx.number_matches('Pikachu-ASRTG05', 'TG05', main_prefix='ASR'))
        self.assertTrue(idx.number_matches('Pikachu-TG05', 'TG05', main_prefix='ASR'))
        self.assertTrue(idx.number_matches('Pikachu-MCD19-5', '5', set_code='MCD19'))


class ApplyTests(unittest.TestCase):
    def test_index_corrects_swapped_same_name_ids(self):
        rows = [row('ecard3-103', '103', catalog_singleton_id='275361')]
        stats = apply(rows)
        self.assertEqual(stats['DIRECT_PRODUCT_URL_ID_CORRECTED'], 1)
        self.assertEqual(rows[0]['catalog_singleton_id'], '275362')
        self.assertEqual(rows[0]['index_previous_id'], '275361')
        self.assertEqual(rows[0]['index_product_url'],
                         'https://www.cardmarket.com/de/Pokemon/Products/Singles/Skyridge/Staryu-SK103')

    def test_id_correction_survives_reapply(self):
        rows = [row('ecard3-103', '103', catalog_singleton_id='275361')]
        apply(rows)
        apply(rows)
        self.assertEqual(rows[0]['index_status'], 'DIRECT_PRODUCT_URL_ID_CORRECTED')
        self.assertEqual(rows[0]['index_previous_id'], '275361')

    def test_plain_number_does_not_pick_holo_subset(self):
        rows = [row('ecard3-10', '10'), row('ecard3-H10', 'H10', 'Holo')]
        apply(rows)
        self.assertTrue(rows[0]['index_product_url'].endswith('/Gengar-V2-SK10'))
        self.assertTrue(rows[1]['index_product_url'].endswith('/Gyarados-V1-SKH10'))

    def test_unique_special_is_priced_automatically(self):
        rows = [row('ecard3-146', '146', 'Holo', foil='cracked-ice')]
        apply(rows)
        self.assertEqual(rows[0]['variant_class'], 'SPECIAL_UNIQUE_FILTER')
        self.assertTrue(rows[0]['index_product_url'].endswith('/Charizard-V1-SK146'))

    def test_colliding_special_goes_to_group_plain_stays_direct(self):
        # Two Cardmarket versions of the number: a human/rule must pick one.
        products = dict(SKYRIDGE, **{'275400': {'slug': 'Skyridge', 'product': 'Charizard-V2-SK146', 'idExpansion': '1538'}})
        catalog = {**CATALOG, 275400: {'idProduct': 275400, 'idExpansion': 1538}}
        rows = [row('ecard3-146', '146', 'Holo', catalog_singleton_id='275300'),
                row('ecard3-146', '146', 'Holo', foil='cracked-ice')]
        idx.apply_index(rows, 'de', products, EXPANSIONS, {}, catalog, {'ecard3': 1538})
        self.assertEqual(rows[0]['index_status'], 'DIRECT_PRODUCT_URL')
        self.assertEqual(rows[1]['index_status'], 'REVIEW_GROUP')
        self.assertEqual(rows[1]['index_review_group'], 'ecard3|cracked-ice')
        self.assertIn('Charizard-V1-SK146', rows[1]['index_candidate_urls'])

    def test_pattern_with_single_cardmarket_product_is_not_separable(self):
        rows = [row('ecard3-145', '145', 'Reverse'), row('ecard3-145', '145', 'Reverse', foil='Meisterball')]
        apply(rows)
        self.assertEqual([r['index_status'] for r in rows], ['DIRECT_PRODUCT_URL', 'SPECIAL_NOT_SEPARABLE'])
        self.assertEqual(rows[1]['index_review_group'], '')
        self.assertEqual(rows[1]['index_product_url'], '')

    def test_reverse_pattern_without_plain_reverse_is_the_reverse(self):
        rows = [row('ecard3-145', '145', 'Normal'), row('ecard3-145', '145', 'Reverse', foil='Energie')]
        apply(rows)
        self.assertEqual([r['index_status'] for r in rows], ['DIRECT_PRODUCT_URL', 'DIRECT_PRODUCT_URL'])

    def test_holo_and_normal_of_same_card_are_one_group(self):
        rows = [row('ecard3-145', '145', 'Normal'), row('ecard3-145', '145', 'Holo')]
        apply(rows)
        self.assertEqual({r['index_review_group'] for r in rows}, {'ecard3|holo-vs-normal'})

    def test_version_rules_resolve_whole_group(self):
        products = {'1': {'slug': 'Base-Set', 'product': 'Abra-V1-BS43', 'idExpansion': '1523'},
                    '2': {'slug': 'Base-Set', 'product': 'Abra-V2-BS43', 'idExpansion': '1523'}}
        exps = {'1523': {'slug': 'Base-Set', 'slugVerified': True, 'crawledAt': 'x'}}
        cat = {1: {'idExpansion': 1523}, 2: {'idExpansion': 1523}}
        rows = [row('base1-43', '43'), row('base1-43', '43', sonderdruck='schattenlos')]
        idx.apply_index(rows, 'de', products, exps, {}, cat, {'base1': 1523})
        self.assertEqual({r['index_review_group'] for r in rows}, {'base1|plain|several-versions', 'base1|shadowless'})
        rules = idx.load_rules({'schema': 1, 'rules': [{'set': 'base1', 'kind': 'shadowless', 'action': 'version', 'version': 'V2'},
                                                       {'set': 'base1', 'kind': 'plain', 'action': 'version', 'version': 'V1'}]})
        idx.apply_index(rows, 'de', products, exps, {}, cat, {'base1': 1523}, rules=rules)
        self.assertEqual([r['index_product_id'] for r in rows], ['1', '2'])
        self.assertEqual({r['index_status'] for r in rows}, {'DIRECT_PRODUCT_URL_RULE'})

    def test_incomplete_expansion_is_not_used(self):
        rows = [row('ecard3-103', '103')]
        idx.apply_index(rows, 'de', SKYRIDGE, {'1538': {'slug': 'Skyridge', 'slugVerified': True}}, {}, CATALOG,
                        {'ecard3': 1538})
        self.assertEqual(rows[0]['index_status'], 'SET_NOT_INDEXED')

    def test_human_route_and_cheap_cards_untouched(self):
        rows = [row('ecard3-145', '145', routing_state='VERIFIED_PRODUCT_ID', catalog_singleton_id='1'),
                row('ecard3-103', '103', existing_price_eur='0.50')]
        apply(rows)
        self.assertEqual(rows[0]['index_status'], 'HUMAN_ROUTE_KEPT')
        self.assertEqual(rows[0]['catalog_singleton_id'], '1')
        self.assertEqual(rows[1]['index_status'], 'GUIDE_PRICE_BELOW_THRESHOLD')

    def test_cheap_card_gets_url_but_keeps_guide_price_route(self):
        rows = [row('ecard3-103', '103', existing_price_eur='0.50', catalog_singleton_id='275361')]
        apply(rows)
        self.assertEqual(rows[0]['index_status'], 'GUIDE_PRICE_BELOW_THRESHOLD')
        self.assertEqual(rows[0]['index_match'], 'DIRECT_PRODUCT_URL_ID_CORRECTED')
        self.assertTrue(rows[0]['index_product_url'].endswith('/Staryu-SK103'))
        self.assertEqual(rows[0]['catalog_singleton_id'], '275361')
        self.assertEqual(rows[0]['index_previous_id'], '')

    def test_plan_includes_cheap_only_expansions_last(self):
        q = {'de': [row('ecard3-103', '103', existing_price_eur='9'), row('base1-1', '1', existing_price_eur='0.5'),
                    row('base1-2', '2', existing_price_eur='0.5')]}
        cat = {275362: {'idProduct': 275362, 'idExpansion': 1538}, 1: {'idProduct': 1, 'idExpansion': 1523}}
        tcg = {('de', 'ecard3-103'): '275362', ('de', 'base1-1'): '1', ('de', 'base1-2'): '1'}
        plan = idx.build_plan(q, tcg, cat, [], {}, {})
        self.assertEqual([e['idExpansion'] for e in plan['expansions']], [1538, 1523])
        self.assertEqual(plan['expansions'][1]['targets'], 0)

    def test_unverified_slug_is_ignored(self):
        expansions = {'1538': {'slug': 'Skyridge', 'slugVerified': False}}
        exps, products = idx.load_index({'schema': 1, 'expansions': expansions},
                                        [json.dumps({'id': '275362', 'slug': 'Skyridge', 'product': 'Staryu-SK103',
                                                     'idExpansion': '1538'})])
        self.assertEqual(products, {})


class CollectorWiringTests(unittest.TestCase):
    def test_collector_uses_index_only_with_matching_id_and_caps_search(self):
        src = (ROOT / 'cardmarket/core/cardmarket-language-browser-collector.ps1').read_text(encoding='utf-8-sig')
        self.assertIn("[string]$case.index_product_id -eq [string]$case.catalog_singleton_id", src)
        self.assertIn("$out.lookup_strategy='EXPANSION_INDEX_DIRECT_V1'", src)
        self.assertIn('@($needsSearch | Select-Object -First $MaxSearchCasesPerBatch)', src)
        self.assertIn("$out.error='EXPANSION_INDEX_'+([string]$case.index_status)", src)
        self.assertIn("$out.review_group=[string]$case.index_review_group", src)
        crawler = (ROOT / 'cardmarket/core/Cardmarket-Expansion-Index.ps1').read_text(encoding='utf-8-sig')
        self.assertIn("Finish 'BLOCKED'", crawler)
        self.assertIn('Wait-RequestGap', crawler)


if __name__ == '__main__':
    unittest.main()
