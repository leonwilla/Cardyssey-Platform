import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv,json,tempfile,unittest
from pathlib import Path
from scripts.cardmarket.admin.cardmarket_scan_monitor import snapshot
class ScanMonitorTests(unittest.TestCase):
 def test_counts_deduplicate_and_do_not_mark_feed_scanned(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);rows=[{'cardyssey_karte':'a','variante_id':'v1','scan_tier':'2','needs_price':'YES',
                    'existing_price_eur':'','existing_source':'','manual_scan_requested_at':'','foil':'','sonderdruck':'','stempel':'[]'},
                   {'cardyssey_karte':'a','variante_id':'v2','scan_tier':'2','needs_price':'YES',
                    'existing_price_eur':'','existing_source':'','manual_scan_requested_at':'','foil':'','sonderdruck':'','stempel':'[]'},
                   {'cardyssey_karte':'b','variante_id':'v1','scan_tier':'4','needs_price':'NO',
                    'existing_price_eur':'0.08','existing_source':'TCGDEX','manual_scan_requested_at':'','foil':'','sonderdruck':'','stempel':'[]'}]
   with (p/'queue-de.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
   with (p/'browser-observations-de.jsonl').open('w') as f:
    for x in [{'card_id':'a','variant_id':'v1','status':'ERROR'},{'card_id':'a','variant_id':'v1','status':'NO_EXACT_NUMBER_SEARCH_HIT'}]:f.write(json.dumps(x)+'\n')
   result=snapshot(p,'de');self.assertEqual(result['totalVariants'],3);self.assertEqual(result['uniqueCards'],2)
   self.assertEqual(result['browserTotal'],2);self.assertEqual(result['browserProcessed'],1)
   self.assertEqual(result['feedOnly'],1);self.assertEqual(result['problemCountInObserved'],1)
 def test_cooldown_respects_both_languages_and_next_eligible_time(self):
  from datetime import datetime,timezone,timedelta
  from scripts.cardmarket.admin.cardmarket_scan_monitor import cooldown_info
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);now=datetime(2026,11,11,13,20,tzinfo=timezone.utc)
   for lang,minutes in [('de',35),('en',15)]:
    (base/f'progress-{lang}.json').write_text(json.dumps({
      'status':'BATCH_COMPLETE_MORE_PENDING',
      'updated_at':(now-timedelta(minutes=minutes)).isoformat()}))
   x=cooldown_info(base,now)
   self.assertTrue(x['cooldownActive'])
   self.assertEqual(x['secondsUntilAllowed'],1800) # EN last batch controls both
   self.assertEqual(len(x['cooldownTriggers']),2)
 def test_last_card_is_most_recent_even_if_key_was_replaced(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d)
   rows=[{'cardyssey_karte':k,'variante_id':'v1','scan_tier':'2','needs_price':'YES',
       'existing_price_eur':'','existing_source':'','manual_scan_requested_at':'',
       'foil':'','sonderdruck':'','stempel':'[]'} for k in ('a','b')]
   with (base/'queue-de.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
   with (base/'browser-observations-de.jsonl').open('w') as f:
    for card,when in [('a','2026-11-11T12:00:00Z'),('b','2026-11-11T12:05:00Z'),('a','2026-11-11T12:06:00Z')]:
     f.write(json.dumps({'card_id':card,'variant_id':'v1','status':'MULTIPLE_SEARCH_HITS',
        'seen_at':when})+'\n')
   x=snapshot(base,'de')
   self.assertEqual(x['lastCard'],'a')
   self.assertEqual([z['cardId'] for z in x['recentEvents']],['a','b'])
 def test_language_allowlist(self):
  with self.assertRaises(ValueError):snapshot(Path('.'),'other')
if __name__=='__main__':unittest.main()
