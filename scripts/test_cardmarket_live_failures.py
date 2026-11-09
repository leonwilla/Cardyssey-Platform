import csv,importlib.util,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
def load(name):
 spec=importlib.util.spec_from_file_location('module_'+name.replace('-','_'),ROOT/name)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
fail=load('cardmarket-live-failures.py');retry=load('cardmarket-retry-one.py')
class Tests(unittest.TestCase):
 def setup(self,td):
  base=Path(td);cols=['cardyssey_karte','variante_id','set_id','kartenname_suche','manual_scan_requested_at']
  for lang in ('de','en'):
   with (base/f'queue-{lang}.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
    for card in ('hgss3-5','2019sm-1'):w.writerow({'cardyssey_karte':card,'variante_id':'v1','set_id':card.rsplit('-',1)[0],'kartenname_suche':card})
  return base
 def test_current_failures_paged_and_historical_hidden(self):
  with tempfile.TemporaryDirectory() as td:
   b=self.setup(td);start=datetime.now(timezone.utc);(b/'full-rescan-epoch.json').write_text(json.dumps({'requestedAt':start.isoformat()}))
   with (b/'browser-observations-de.jsonl').open('w') as f:
    for card,status,seen in [('2019sm-1','NO_EXACT_NUMBER_SEARCH_HIT',start-timedelta(days=2)),('hgss3-5','FILTER_UNAVAILABLE',start+timedelta(seconds=1))]:
     f.write(json.dumps({'card_id':card,'variant_id':'v1','status':status,'seen_at':seen.isoformat()})+'\n')
   result=fail.list_failures(b,'de')
   self.assertEqual(result['total'],1);self.assertEqual(result['items'][0]['type'],'TECHNISCH')
   self.assertEqual(fail.list_failures(b,'de',scope='all')['total'],2)
 def test_retry_only_requested_variant(self):
  with tempfile.TemporaryDirectory() as td:
   b=self.setup(td);r=retry.retry('de','hgss3-5','v1',base=b)
   self.assertTrue(r['ok'])
   with (b/'queue-de.csv').open() as f:rows=list(csv.DictReader(f))
   self.assertTrue(rows[0]['manual_scan_requested_at'])
   self.assertFalse(rows[1]['manual_scan_requested_at'])
 def test_missing_required_fields_are_visible_instead_of_card_missing(self):
  self.assertEqual(fail.classify('MISSING_REQUIRED_SCAN_FIELDS'),'DATEN_FEHLEN')
  self.assertEqual(fail.classify('FILTER_UNAVAILABLE'),'TECHNISCH')
 def test_no_unknown_queue_row(self):
  with tempfile.TemporaryDirectory() as td:
   b=self.setup(td)
   with self.assertRaisesRegex(ValueError,'card_variant_not_in_current_queue'):retry.retry('de','fake-1','v1',base=b)
if __name__=='__main__':unittest.main()
