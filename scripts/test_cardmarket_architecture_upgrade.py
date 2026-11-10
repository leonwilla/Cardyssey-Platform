"""Regression checks for safe scoring, observed-set guards and guide-only data."""
import csv,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def load(filename):
    spec=importlib.util.spec_from_file_location(filename.replace('-','_'),ROOT/'scripts'/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
guards=load('cardmarket-build-observed-set-guards.py')
guide=load('cardmarket-build-guide-diagnostics.py')

class CardmarketUpgrade(unittest.TestCase):
    def test_observed_set_path_requires_five_distinct_cards_and_no_conflicts(self):
        with tempfile.TemporaryDirectory() as t:
            b=Path(t)
            rows=[]
            events=[]
            for n in range(6):
                card=f'sv09-{n+1:03d}';pid=str(800000+n)
                rows.append({'cardyssey_karte':card,'variante_id':'normal',
                             'set_id':'sv09','catalog_singleton_id':pid,
                             'catalog_expansion_id':'6001'})
                events.append({'card_id':card,'variant_id':'normal','product_id':pid,
                               'catalog_direct_id_verified':True,'card_number_url_verified':True,
                               'url':f'https://www.cardmarket.com/de/Pokemon/Products/Singles/Journey-Together/Test-V1-SVI{n+1:03d}'})
            with (b/'queue-de.csv').open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
            with (b/'browser-observations-de.jsonl').open('w') as f:
                for x in events:f.write(json.dumps(x)+'\n')
            result=guards.derive(base=b)
            self.assertEqual(result['setSlugs']['sv09']['distinctLiveCards'],6)
            self.assertEqual(result['setSlugs']['sv09']['setSlug'],'Journey-Together')
            events[-1]['url']=events[-1]['url'].replace('Journey-Together','Different-Expansion')
            with (b/'browser-observations-de.jsonl').open('w') as f:
                for x in events:f.write(json.dumps(x)+'\n')
            result=guards.derive(base=b)
            self.assertNotIn('sv09',result['setSlugs'])
            self.assertIn('sv09',result['ambiguousExcluded'])
    def test_price_guide_is_only_diagnostic_not_eligible_for_print_price(self):
        with tempfile.TemporaryDirectory() as t:
            b=Path(t);cache=b/'cache';cache.mkdir()
            for lang in ('de','en'):
                with (b/f'queue-{lang}.csv').open('w',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=['cardmarket_ids','catalog_singleton_id'])
                    w.writeheader();w.writerow({'cardmarket_ids':'836551,836552','catalog_singleton_id':''})
            p=cache/(hashlib.sha256(guide.URL.encode()).hexdigest()+'.json')
            items=[{'idProduct':836551,'trend':7.58,'avg30':7.80,'trend-holo':7.58,'avg30-holo':7.80}]
            items += [{'idProduct':i+1000000,'trend':0} for i in range(50000)]
            p.write_text(json.dumps({'createdAt':'2026-11-09T02:50:26+0100','priceGuides':items}))
            result=guide.build(base=b,cache=cache)
            self.assertFalse(result['canPublishAsLanguagePrintPrice'])
            self.assertEqual(result['products']['836551']['avg30'],7.8)
            self.assertNotIn('language',result['products']['836551'])
            self.assertNotIn('836552',result['products'])
    def test_live_smoke_no_price_publication(self):
        p=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector/probe-score-filter-20261110/browser-observations-de.jsonl')
        if not p.is_file():self.skipTest('No local browser probe')
        seen={}
        with p.open(encoding='utf-8-sig') as f:
            for line in f:
                x=json.loads(line);seen[x['card_id']]=x
        self.assertEqual(len(seen),3)
        self.assertEqual(seen['sve-015']['status'],'MULTIPLE_SEARCH_HITS')
        self.assertEqual(seen['sv09-128']['score_matching_status'],'UNIQUE_SET_NUMBER_PAGE_CANDIDATE')
        self.assertFalse(seen['sv09-128']['official_guide_product_aggregate']['can_publish_language_print_price'])
        self.assertEqual(seen['sv01-013']['filter_mode'],'FORM_SUBMISSION_DOM_VERIFIED')
        self.assertIsNone(seen['sv01-013'].get('median_all_offers_eur'))
    def test_fail_closed_wiring(self):
        source=(ROOT/'scripts/cardmarket-language-browser-collector.ps1').read_text(encoding='utf-8-sig')
        for marker in ('CARDMARKET_SCORE_MODULE_MISSING','CANONICAL_URL_DOM_VERIFIED',
                       'FORM_SUBMISSION_DOM_VERIFIED','PROVIDER_URL_FILTER_NOT_VERIFIED',
                       'SCORED_PAGE_NOT_IN_CATALOG_CANDIDATES','SET_NOT_INDEPENDENTLY_VERIFIED',
                       'OFFICIAL_CARDMARKET_PRODUCT_GUIDE_NOT_VARIANT_PRICE',
                       'can_publish_language_print_price=$false',
                       'DIRECT_ID_LOOKUP_TIMEOUT_OR_UNAVAILABLE'):
            self.assertIn(marker,source)
        ui=(ROOT/'web/app/admin/prices/page.tsx').read_text()
        self.assertIn('kein DE/EN-Variantenpreis',ui)
        self.assertIn('Kandidat {i+1} ansehen',ui)
if __name__=='__main__':unittest.main()
