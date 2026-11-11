"""Fail-closed regression suite: official guide is NOT a DE/EN NM price."""
from __future__ import annotations
import csv,importlib.util,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
import sys
SCRIPT=Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPT))
import cardmarket_delta_scan as d
from cardmarket_game_profile import load_game_profile

NOW=datetime(2026,11,11,13,0,tzinfo=timezone.utc)
PREVIOUS=NOW-timedelta(days=7)
CURRENT=NOW-timedelta(hours=1)
OLD={"gameId":6,"createdAt":PREVIOUS.isoformat(),
     "products":{"836551":{"avg30":"10","trend":"9"}}}
NEW={"gameId":6,"createdAt":CURRENT.isoformat(),
     "products":{"836551":{"avg30":"10.9","trend":"9.8"}}}
def row(**kw):
    x={"cardyssey_karte":"sv99-001","variante_id":"v-normal",
       "drucktyp":"Normal","foil":"","stempel":"[]","sonderdruck":"",
       "cardmarket_ids":"836551","needs_price":"NO","scan_tier":"2",
       "manual_scan_requested_at":"","existing_price_eur":"10.00",
       "existing_source":"CARDMARKET_WEB"}
    x.update(kw);return x
def cached(**kw):
    x={"price":10,"status":"PRICE_FOUND","primary_provider":"CARDMARKET",
       "verification_state":"VERIFIED_PRODUCT_ID",
       "product_id":"836551","selected_product_id":"836551","manual_confirmed":True}
    x.update(kw);return x
def observed(**kw):
    x={"language":"de","card_id":"sv99-001","variant_id":"v-normal",
       "product_id":"836551","identity_confirmed":True,
       "all_pages_complete":True,"access_mode":"AUTHENTICATED",
       "status":"COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED",
       "pagination_failure":"","verified_lang_nm_offers":18,
       "seen_at":(NOW-timedelta(days=5)).isoformat()}
    x.update(kw);return x

class GameProfileTests(unittest.TestCase):
    def test_pokemon_endpoints(self):
        p=load_game_profile()
        self.assertEqual(p['game_id'],6)
        self.assertEqual(p['game_path'],'Pokemon')
        self.assertEqual(p['product_url'],'https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json')
        self.assertEqual(p['price_url'],'https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json')
    def test_game_id_consistency_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'profile.json'
            base=json.loads((SCRIPT.parent/'config/cardmarket-game-profile.json').read_text())
            for change in ({'game_id':7},{'base_url':'https://evil.example'},
                           {'catalog_filename':'products_singles_9.json'}):
                modified=json.loads(json.dumps(base))
                modified['profiles']['pokemon'].update(change)
                p.write_text(json.dumps(modified))
                with self.assertRaises(ValueError):load_game_profile(p)
    def test_unknown_future_profile_cannot_be_inferred(self):
        with self.assertRaises(ValueError):load_game_profile(name='one_piece')

class DeltaGateTests(unittest.TestCase):
    def runcheck(self,r=None,c=None,o=None,old=OLD,new=NEW,now=NOW,lang='de'):
        return d.can_skip(r or row(),c or cached(),o or observed(language=lang),
                          old['products'].get('836551') if old else None,
                          new['products'].get('836551') if new else None,now,
                          d.parsed_time(old['createdAt']) if old else None,
                          d.parsed_time(new['createdAt']) if new else None,lang)
    def test_9_percent_plus_stable_human_confirmed_de_print_skips(self):
        self.assertIsNotNone(self.runcheck())
    def test_english_language_not_inferred_from_german(self):
        self.assertIsNone(self.runcheck(o=observed(language='de'),lang='en'))
        self.assertIsNotNone(self.runcheck(o=observed(language='en'),lang='en'))
    def test_both_guide_metrics_must_be_below_ten_percent(self):
        ten=dict(NEW,products={'836551':{'avg30':'11','trend':'9.5'}})
        self.assertIsNone(self.runcheck(new=ten))
        changed=dict(NEW,products={'836551':{'avg30':'10.2','trend':'10.0'}})
        self.assertIsNone(self.runcheck(new=changed))
        self.assertIsNotNone(self.runcheck())
    def test_missing_guide_or_no_prior_baseline_never_skips(self):
        self.assertIsNone(self.runcheck(old=None))
        self.assertIsNone(self.runcheck(new=dict(NEW,products={})))
        self.assertIsNone(self.runcheck(new=dict(NEW,products={'836551':{'trend':9.1}})))
    def test_stale_or_same_feed_or_old_observation_never_skips(self):
        self.assertIsNone(self.runcheck(old=dict(OLD,createdAt=NEW['createdAt'])))
        self.assertIsNone(self.runcheck(old=dict(OLD,createdAt=(NOW-timedelta(days=32)).isoformat())))
        self.assertIsNone(self.runcheck(new=dict(NEW,createdAt=(NOW-timedelta(days=3)).isoformat())))
        self.assertIsNone(self.runcheck(o=observed(seen_at=(NOW-timedelta(days=29)).isoformat())))
        self.assertIsNone(self.runcheck(o=observed(seen_at=(NOW+timedelta(days=2)).isoformat())))
    def test_never_skip_15_eur_or_no_price_or_no_price_flag(self):
        self.assertIsNone(self.runcheck(c=cached(price=15)))
        self.assertIsNotNone(self.runcheck(c=cached(price=14.99)))
        self.assertIsNone(self.runcheck(c=cached(price=0,status='NO_PRICE')))
        self.assertIsNone(self.runcheck(r=row(needs_price='YES')))
    def test_special_prints_manual_requests_never_skip(self):
        for r in [row(foil='Masterball'),row(stempel='["Staff"]'),
                  row(sonderdruck='Cosmos'),row(drucktyp='Reverse'),
                  row(manual_scan_requested_at=NOW.isoformat())]:
            with self.subTest(row=r):self.assertIsNone(self.runcheck(r=r))
    def test_unverified_routes_and_wrong_product_never_skip(self):
        for c in [cached(manual_confirmed=False),cached(verification_state='SOURCE_ONLY'),
                  cached(primary_provider='TCGDEX'),cached(product_id='999999'),
                  cached(selected_product_id='999999')]:
            with self.subTest(cache=c):self.assertIsNone(self.runcheck(c=c))
        self.assertIsNone(self.runcheck(r=row(cardmarket_ids='836551,837000')))
    def test_incomplete_offer_pages_never_confirm_success(self):
        for o in [observed(all_pages_complete=False),observed(identity_confirmed=False),
                  observed(status='FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE'),
                  observed(access_mode='PUBLIC_LIMITED'),
                  observed(pagination_failure='MORE_OFFERS_STILL_VISIBLE'),
                  observed(verified_lang_nm_offers=0),
                  observed(product_id='999999'),observed(verified_lang_nm_offers='BAD')]:
            with self.subTest(observation=o):self.assertIsNone(self.runcheck(o=o))
    def test_evaluate_only_marks_evidence_backed_row(self):
        rows=[row(),row(variante_id='v-stamped',stempel='["Staff"]')]
        data,stats=d.evaluate(rows,{('sv99-001','v-normal'):cached()},{
             ('sv99-001','v-normal'):observed()
             },OLD,NEW,NOW,'de')
        self.assertEqual(len(data),2)
        self.assertEqual(data[0]['delta_browser_skip'],'YES')
        self.assertEqual(data[0]['needs_price'],'NO')
        self.assertEqual(data[1]['delta_browser_skip'],'NO')
        self.assertEqual(stats['guide_stable_skip'],1)
        self.assertEqual(rows[0].get('delta_browser_skip'),None)
    def test_bad_guide_fail_closed(self):
        self.assertIsNone(d.guide_pair({'avg30':None,'trend':4}))
        self.assertIsNone(d.guide_pair({'avg30':-2,'trend':3}))
        self.assertIsNone(d.guide_pair({'avg30':'nan','trend':3}))
    def test_active_scanner_blocks_weekly_queue_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            b=Path(t)
            (b/'progress-de.json').write_text(json.dumps({
               'status':'RUNNING','updated_at':NOW.isoformat()}))
            with self.assertRaises(RuntimeError):d.lock_queue_active(b,NOW)
    def test_apply_first_run_baseline_and_second_run_safe_gate(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)
            for lang in ('de','en'):
                with (base/f'queue-{lang}.csv').open('w',encoding='utf-8-sig',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=row().keys());w.writeheader();w.writerow(row())
                with (base/f'browser-observations-{lang}.jsonl').open('w') as f:
                    f.write(json.dumps(observed(language=lang))+'\n')
            cache={lang:{('sv99-001','v-normal'):cached()} for lang in ('de','en')}
            # First new guide doesn't yet have a baseline: zero skip.
            with patch.object(d,'compile_guide',return_value=OLD):
                a=d.apply(base=base,feed={},cache_by_language=cache,now=PREVIOUS+timedelta(hours=1),dry_run=False)
            self.assertEqual(a['languages']['de']['safeSkips'],0)
            self.assertFalse(a['priceUpdatedAtTouched'])
            self.assertTrue((base/'cardmarket-guide-delta-state.json').exists())
            # Second Guide changed by 9%, now eligible for both languages.
            with patch.object(d,'compile_guide',return_value=NEW):
                a=d.apply(base=base,feed={},cache_by_language=cache,now=NOW,dry_run=False)
            self.assertEqual(a['languages']['de']['safeSkips'],1)
            self.assertEqual(a['languages']['en']['safeSkips'],1)
            self.assertFalse(a['cacheTouched'])
            self.assertEqual(a['pricesPublished'],0)
            for lang in ('de','en'):
                with (base/f'queue-{lang}.csv').open(encoding='utf-8-sig',newline='') as f:
                    values=list(csv.DictReader(f))
                self.assertEqual(len(values),1)
                self.assertEqual(values[0]['delta_browser_skip'],'YES')
            self.assertEqual(json.loads((base/'cardmarket-guide-delta-state.json').read_text())['createdAt'],NEW['createdAt'])

if __name__=='__main__':unittest.main()
