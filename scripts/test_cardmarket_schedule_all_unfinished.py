"""One-time failed-only requeue leaves successful and historical rows untouched."""
import csv,importlib.util,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('outstanding',ROOT/'scripts/cardmarket-schedule-all-unfinished.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class RecoveryTests(unittest.TestCase):
 def test_all_open_current_epoch_once_old_and_success_untouched(self):
  with tempfile.TemporaryDirectory() as t:
   base=Path(t)
   epoch=datetime(2026,11,9,19,30,tzinfo=timezone.utc)
   (base/'full-rescan-epoch.json').write_text(json.dumps({'requestedAt':epoch.isoformat()}))
   cols=['cardyssey_karte','variante_id','set_id','drucktyp','cardmarket_ids',
         'manual_scan_requested_at','existing_price_eur']
   for lang in ('de','en'):
    rows=[{'cardyssey_karte':str(i),'variante_id':'v1','set_id':'sve','drucktyp':'Reverse',
           'cardmarket_ids':'321'+str(i),'manual_scan_requested_at':'','existing_price_eur':'0.02'} for i in range(5)]
    with (base/f'queue-{lang}.csv').open('w',newline='',encoding='utf-8-sig') as f:
     writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows(rows)
    cases=[
     ('0','MULTIPLE_SEARCH_HITS',epoch+timedelta(hours=1)),
     ('1','FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE',epoch+timedelta(hours=1)),
     ('2','COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED',epoch+timedelta(hours=1)),
     ('3','NO_EXACT_NUMBER_SEARCH_HIT',epoch-timedelta(days=1))]
    with (base/f'browser-observations-{lang}.jsonl').open('w') as f:
     for cid,status,when in cases:
      f.write(json.dumps({'card_id':cid,'variant_id':'v1',
         'status':status,'seen_at':when.isoformat()})+'\n')
   before=(base/'queue-de.csv').read_bytes()
   out=mod.audit_and_schedule(base=base,apply=False,now=epoch+timedelta(hours=2))
   self.assertEqual(out['languages']['de']['requeuedCurrentFailures'],2)
   self.assertEqual(out['languages']['en']['requeuedCurrentFailures'],2)
   self.assertEqual(out['languages']['de']['unscannedAlreadyDue'],1)
   self.assertEqual(out['languages']['de']['historicalAlreadyDue'],1)
   self.assertEqual(out['languages']['de']['completedUnchanged'],1)
   self.assertEqual(before,(base/'queue-de.csv').read_bytes())
   old_report=mod.REPORT;mod.REPORT=base/'reports'
   try:out=mod.audit_and_schedule(base=base,apply=True,now=epoch+timedelta(hours=2))
   finally:mod.REPORT=old_report
   for lang in ('de','en'):
    with (base/f'queue-{lang}.csv').open(encoding='utf-8-sig') as f:
     rows={x['cardyssey_karte']:x for x in csv.DictReader(f)}
    self.assertTrue(rows['0']['manual_scan_requested_at'])
    self.assertTrue(rows['1']['manual_scan_requested_at'])
    for n in ('2','3','4'):self.assertFalse(rows[n]['manual_scan_requested_at'])
    self.assertEqual(rows['0']['cardmarket_ids'],'3210')
    self.assertEqual(rows['0']['existing_price_eur'],'0.02')
 def test_all_retryable_known_statuses_explicit(self):
  self.assertIn('PRODUCT_ID_NOT_VERIFIED_FOR_CARD',mod.RETRYABLE)
  self.assertIn('BLOCKED',mod.RETRYABLE)
  self.assertIn('DEFERRED_SOCKET',mod.RETRYABLE)
  self.assertNotIn('COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED',mod.RETRYABLE)
if __name__=='__main__':unittest.main()
