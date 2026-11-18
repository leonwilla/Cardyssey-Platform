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
   self.assertEqual(x['secondsUntilAllowed'],300) # EN last batch controls both
   self.assertEqual(len(x['cooldownTriggers']),2)
 def test_login_required_does_not_extend_cooldown_for_guest_mode(self):
  from datetime import datetime,timezone
  from scripts.cardmarket.admin.cardmarket_scan_monitor import cooldown_info
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);now=datetime(2026,11,13,13,30,tzinfo=timezone.utc)
   (root/'progress-de.json').write_text(json.dumps({
       'status':'LOGIN_REQUIRED','updated_at':'2026-11-13T13:29:00Z'}))
   (root/'progress-en.json').write_text(json.dumps({
       'status':'BATCH_COMPLETE_MORE_PENDING','updated_at':'2026-11-13T12:00:00Z'}))
   result=cooldown_info(root,now)
   self.assertFalse(result['cooldownActive'])
   self.assertIsNone(result['blocking'])
 def test_cross_language_cooldown_identifies_origin_and_expires(self):
  from datetime import datetime,timezone
  from scripts.cardmarket.admin.cardmarket_scan_monitor import cooldown_info
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);now=datetime(2026,11,13,13,30,tzinfo=timezone.utc)
   (root/'progress-de.json').write_text(json.dumps({
       'status':'BLOCKED','updated_at':'2026-11-13T13:20:00Z'}))
   (root/'progress-en.json').write_text(json.dumps({
       'status':'BATCH_COMPLETE_MORE_PENDING','updated_at':'2026-11-13T12:00:00Z'}))
   result=cooldown_info(root,now)
   self.assertTrue(result['cooldownActive'])
   self.assertEqual(result['blocking']['language'],'de')
   self.assertEqual(result['blocking']['status'],'BLOCKED')
   self.assertTrue(result['languageCooldowns']['de']['active'])
   self.assertFalse(result['languageCooldowns']['en']['active'])
 def test_monitor_distinguishes_collector_checkpoint_from_rescan_epoch(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   rows=[{'cardyssey_karte':'a','variante_id':'v1','scan_tier':'2','needs_price':'YES',
       'existing_price_eur':'','existing_source':'','manual_scan_requested_at':'',
       'foil':'','sonderdruck':'','stempel':'[]'}]
   with (root/'queue-de.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
   (root/'progress-de.json').write_text(json.dumps({'status':'BLOCKED','done':726,
     'total':16381,'last_card':'a','updated_at':'2026-11-13T13:23:00Z'}))
   (root/'browser-session-status.json').write_text(json.dumps({'status':'AVAILABLE',
     'login':'AUTHENTICATED','checkedAt':'2026-11-13T13:21:09Z'}))
   with (root/'browser-observations-de.jsonl').open('w') as stream:
    stream.write(json.dumps({'card_id':'a','variant_id':'v1','status':'BLOCKED',
       'seen_at':'2026-11-13T13:21:20Z','catalog_direct_id_challenge_title':'Nur einen Moment…',
       'catalog_direct_id_challenge_path':'/Pokemon/Products'})+'\n')
   result=snapshot(root,'de')
   self.assertEqual(result['collectorProcessed'],726)
   self.assertEqual(result['collectorTotal'],16381)
   self.assertEqual(result['lastIncident']['kind'],'DIRECT_ID_INTERSTITIAL')
   self.assertEqual(result['lastIncident']['cardId'],'a')
   self.assertEqual(result['browserSession']['status'],'AVAILABLE')
   self.assertIsNotNone(result['statusSnapshotAt'])

   (root/'progress-de.json').write_text(json.dumps({'status':'BLOCKED','done':726,
     'total':16381,'updated_at':'2026-11-13T19:23:00Z','provider_block_stage':'SESSION_BOOTSTRAP'}))
   result=snapshot(root,'de')
   self.assertEqual(result['lastIncident'],{'kind':'SESSION_BOOTSTRAP','at':'2026-11-13T19:23:00Z'})

 def test_fresh_available_releases_latest_block_but_not_batch_pause(self):
  from datetime import datetime, timezone
  from scripts.cardmarket.admin.cardmarket_scan_monitor import cooldown_info
  with tempfile.TemporaryDirectory() as path:
   b=Path(path)
   now=datetime(2026,11,13,14,49,tzinfo=timezone.utc)
   def progress(language,status,minute):
    (b/f'progress-{language}.json').write_text(json.dumps({
     'status':status,'updated_at':f'2026-11-13T14:{minute}:00Z'}))
   def session(status,minute):
    (b/'browser-session-status.json').write_text(json.dumps({
     'status':status,'checkedAt':f'2026-11-13T14:{minute}:00Z'}))
   progress('de','BLOCKED',43)
   progress('en','BATCH_COMPLETE_MORE_PENDING',41)
   for status,minute in [('AVAILABLE',42),('AVAILABLE',45),('BLOCKED',48),('BROWSER_UNAVAILABLE',48)]:
    session(status,minute)
    result=cooldown_info(b,now)
    self.assertEqual(result['blocking']['minutes'],240)
   session('AVAILABLE',48)
   self.assertFalse(cooldown_info(b,now)['cooldownActive'])
   progress('en','BATCH_COMPLETE_MORE_PENDING',46)
   self.assertEqual(cooldown_info(b,now)['blocking']['minutes'],20)
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
