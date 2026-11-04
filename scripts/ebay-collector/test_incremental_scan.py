import json
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
from incremental_scan import since_date,saved_baseline,scan_window,mark_success
from weekly_scan import due_set

class ScanCursorTests(unittest.TestCase):
 def test_overlap_two_days(self):
  self.assertEqual(since_date('2026-11-04T12:00:00+00:00'),'2026-11-02')
 def test_old_success_report_is_accepted_only_if_complete_and_query_matches(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'sv01'
   root.mkdir()
   archive=Path(tmp)/'sv01-history-1234'/'sv01-001'
   archive.mkdir(parents=True)
   report={'config':{'query':'Tannza 001/198 deutsch','language':'de','max_age_days':36500},'pages':[{'status':'OK'}],
           'collected_at':'2026-11-01T10:00:00+00:00'}
   (archive/'sales.json').write_text(json.dumps(report))
   self.assertEqual(saved_baseline('sv01-001','Tannza 001/198 deutsch',root).date().isoformat(),'2026-11-01')
   self.assertIsNone(saved_baseline('sv01-001','Other query',root))
   report['config']['max_age_days']=30
   (archive/'sales.json').write_text(json.dumps(report))
   self.assertIsNone(saved_baseline('sv01-001','Tannza 001/198 deutsch',root))
   report['config']['max_age_days']=36500
   report['pages']=[{'status':'SERVICE_ERROR'}]
   (archive/'sales.json').write_text(json.dumps(report))
   self.assertIsNone(saved_baseline('sv01-001','Tannza 001/198 deutsch',root))
 def test_checkpoint_from_db_overrides_archived_reports(self):
  with patch('incremental_scan.read_cursor',return_value='2026-11-04T12:00:00Z'):
   since,source,when=scan_window('sv01-001','anything',Path('/missing'))
   self.assertEqual((since,source),('2026-11-02','DATABASE'))
   self.assertEqual(when.date().isoformat(),'2026-11-04')
 def test_db_checkpoint_update_rejects_backwards_advance(self):
  with patch('incremental_scan.db') as db:
   mark_success('sv01-001','Tannza 001/198',datetime(2026,11,4,tzinfo=timezone.utc))
   sql=db.call_args.args[0]
   self.assertIn('GREATEST',sql)
   self.assertIn('sv01-001',sql)

class WeeklySchedulerTests(unittest.TestCase):
 def test_due_every_seven_days_and_respects_complete_manual_runs(self):
  now=datetime(2026,11,4,tzinfo=timezone.utc)
  recent=(now-timedelta(days=3)).isoformat()
  schedule={s:{'last_attempt':recent} for s in ('30th','30th-c','mep','sv02','sv01')}
  self.assertIsNone(due_set(now,schedule,{}))
  schedule['sv02']['last_attempt']=(now-timedelta(days=8)).isoformat()
  self.assertEqual(due_set(now,schedule,{}),'sv02')
  jobs={'sv02':{'status':'COMPLETE','checked_at':recent}}
  self.assertIsNone(due_set(now,schedule,jobs))

if __name__=='__main__':unittest.main()
