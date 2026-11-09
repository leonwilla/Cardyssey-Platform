import csv,importlib.util,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
m_path=Path(__file__).with_name('cardmarket-reset-rescan.py')
s=importlib.util.spec_from_file_location('reset_cm',m_path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ResetTests(unittest.TestCase):
 def test_reset_starts_new_epoch_but_preserves_previous_scan_history(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp)
   for lang in ('de','en'):
    (base/f'queue-{lang}.csv').write_text('card,variant\n'+('x,v\n'*1000))
    (base/f'progress-{lang}.json').write_text(json.dumps({'status':'BLOCKED','done':42,'total':1000,'file':'history'}))
    (base/f'browser-observations-{lang}.jsonl').write_text('historic row\n')
   now=datetime(2026,11,9,14,0,tzinfo=timezone.utc)
   result=m.reset(base=base,check_process=False,now=now)
   self.assertEqual(result['startedAt'],now.isoformat())
   for lang in ('de','en'):
    p=json.loads((base/f'progress-{lang}.json').read_text())
    self.assertEqual(p['done'],0);self.assertEqual(p['status'],'QUEUED');self.assertEqual(p['file'],'history')
    self.assertEqual((base/f'browser-observations-{lang}.jsonl').read_text(),'historic row\n')
   self.assertEqual(json.loads((base/'full-rescan-epoch.json').read_text())['requestedAt'],now.isoformat())
if __name__=='__main__':unittest.main()
