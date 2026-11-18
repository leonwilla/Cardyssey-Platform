import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from scripts.cardmarket.admin.cardmarket_scan_monitor import snapshot
class RescanEpochTests(unittest.TestCase):
 def test_old_observations_preserved_but_not_in_new_cycle(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);keys=[('a','v1'),('a','v2')]
   with (p/'queue-de.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['cardyssey_karte','variante_id','scan_tier','needs_price','existing_price_eur']);w.writeheader()
    for card,variant in keys:w.writerow({'cardyssey_karte':card,'variante_id':variant,'scan_tier':'1','needs_price':'NO','existing_price_eur':'10'})
   start=datetime(2026,11,9,13,0,tzinfo=timezone.utc)
   (p/'full-rescan-epoch.json').write_text(json.dumps({'requestedAt':start.isoformat()}))
   with (p/'browser-observations-de.jsonl').open('w') as f:
    for i,(card,variant) in enumerate(keys):f.write(json.dumps({'card_id':card,'variant_id':variant,'status':'MAPPED_NO_PRICE_REQUIRED','seen_at':(start+timedelta(seconds=1) if i else start-timedelta(days=1)).isoformat()})+'\n')
   x=snapshot(p,'de')
   self.assertEqual(x['browserProcessed'],2)
   self.assertEqual(x['rescanProcessed'],1)
   self.assertIsNotNone(x['rescanStartedAt'])
if __name__=='__main__':unittest.main()
