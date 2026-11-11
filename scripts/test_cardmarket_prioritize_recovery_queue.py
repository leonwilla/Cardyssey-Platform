"""Queue-priority invariants: stable keys, special prints, no lost entries."""
import importlib.util
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
import csv,json
spec=importlib.util.spec_from_file_location('recovery_priority',Path(__file__).with_name('cardmarket-prioritize-recovery-queue.py'))
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class PrioritizeRecoveryTests(unittest.TestCase):
 def make(self,card,special='',tier='4',manual=''):
  return {'cardyssey_karte':card,'variante_id':'v1','set_id':'sv','drucktyp':'Normal',
    'foil':special,'sonderdruck':'','stempel':'[]','scan_tier':tier,
    'manual_scan_requested_at':manual,'existing_price_eur':'0.15'}
 def test_prints_and_manual_failures_before_bulk(self):
  now=datetime.now(timezone.utc)
  rows=[self.make('bulk'),self.make('fail',tier='2',manual=now.isoformat()),
    self.make('pokeball','Pokeball'),self.make('mapped','Meisterball'),
    self.make('old-error',tier='2')]
  latest={('old-error','v1'):{'status':'NO_EXACT_NUMBER_SEARCH_HIT','seen_at':now.isoformat()},
    ('fail','v1'):{'status':'ERROR','seen_at':(now-timedelta(days=1)).isoformat()}}
  output,report=mod.prioritize(rows,latest,{('mapped','v1')})
  self.assertEqual([r['cardyssey_karte'] for r in output],
                   ['mapped','pokeball','fail','old-error','bulk'])
  self.assertEqual(len(output),5)
  self.assertEqual(output[0]['existing_price_eur'],'0.15')
 def test_same_card_keeps_distinct_variant_rows(self):
  rows=[self.make('wattzapf','Meisterball'),self.make('wattzapf','Pokeball')]
  rows[1]['variante_id']='v2'
  output,report=mod.prioritize(rows,{},set())
  self.assertEqual(len(output),2)
  self.assertEqual(len({(r['cardyssey_karte'],r['variante_id']) for r in output}),2)
 def test_normal_reverse_not_special_by_default(self):
  row=self.make('regular')
  self.assertFalse(mod.is_special(row))
  row['drucktyp']='Reverse'
  self.assertFalse(mod.is_special(row))
  row['stempel']='["Professorenprogramm"]'
  self.assertTrue(mod.is_special(row))
 def test_dry_run_no_mutations_and_apply_atomic(self):
  with tempfile.TemporaryDirectory() as t:
   base=Path(t)
   fields=list(self.make('x').keys())
   for lang in ('de','en'):
    with (base/f'queue-{lang}.csv').open('w',newline='',encoding='utf-8-sig') as f:
     w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([
         self.make('bulk'),self.make('rare','Pokeball')])
    (base/f'browser-observations-{lang}.jsonl').write_text('')
   a=(base/'queue-de.csv').read_bytes()
   report=mod.run(base=base,apply=False,candidates={('de','rare','v1')})
   self.assertEqual(a,(base/'queue-de.csv').read_bytes())
   self.assertEqual(report['languages']['de']['openMappingCasesInQueue'],1)
   mod.run(base=base,apply=True,candidates={('de','rare','v1')})
   with (base/'queue-de.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
   self.assertEqual([x['cardyssey_karte'] for x in rows],['rare','bulk'])
   self.assertEqual(rows[0]['existing_price_eur'],'0.15')
 def test_one_time_recheck_promotes_only_open_failed_case(self):
  with tempfile.TemporaryDirectory() as t:
   base=Path(t)
   stamp=datetime(2026,11,11,13,0,tzinfo=timezone.utc)
   previous=stamp-timedelta(hours=2)
   fields=list(self.make('a').keys())
   for lang in ('de','en'):
    with (base/f'queue-{lang}.csv').open('w',newline='',encoding='utf-8-sig') as f:
     w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([
       self.make('open','Pokeball'),self.make('success','Masterball'),self.make('bulk')])
    with (base/f'browser-observations-{lang}.jsonl').open('w') as f:
     for cid,status in [('open','PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED'),
                        ('success','COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED')]:
      f.write(json.dumps({'card_id':cid,'variant_id':'v1','status':status,'seen_at':previous.isoformat()})+'\n')
   cases={(lang,'open','v1') for lang in ('de','en')}
   first=mod.run(base=base,apply=True,candidates=cases,recheck_open=True,now=stamp)
   self.assertEqual(first['languages']['de']['specialRecheckMarked'],1)
   self.assertEqual(first['languages']['en']['specialRecheckMarked'],1)
   self.assertTrue((base/'open-print-recheck-once-20261111.json').exists())
   for lang in ('de','en'):
    with (base/f'queue-{lang}.csv').open(encoding='utf-8-sig') as f:
     rows={r['cardyssey_karte']:r for r in csv.DictReader(f)}
    self.assertEqual(rows['open']['manual_scan_requested_at'],stamp.isoformat())
    self.assertEqual(rows['success']['manual_scan_requested_at'],'')
   next_run=mod.run(base=base,apply=True,candidates=cases,recheck_open=True,now=stamp+timedelta(hours=6))
   self.assertTrue(next_run['recheckAlreadyScheduled'])
   self.assertEqual(next_run['languages']['de']['specialRecheckMarked'],0)
if __name__=='__main__':unittest.main()
