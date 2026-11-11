"""Never drop pending manual variant scans during S3 guide weekly refresh."""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv,importlib.util,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('weekly_safe',source_path('run-cardmarket-identity-weekly.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TestWeeklyManualPreservation(unittest.TestCase):
    def test_manual_refresh_kept_and_newer_timestamp_retained(self):
        with tempfile.TemporaryDirectory() as t:
            q=Path(t)/'queue-de.csv'
            with q.open('w',newline='',encoding='utf-8-sig') as f:
                w=csv.DictWriter(f,fieldnames=['cardyssey_karte','variante_id','needs_price','manual_scan_requested_at'])
                w.writeheader()
                w.writerow({'cardyssey_karte':'sv01-013','variante_id':'pokeball','needs_price':'YES','manual_scan_requested_at':''})
                w.writerow({'cardyssey_karte':'sv01-013','variante_id':'normal','needs_price':'NO','manual_scan_requested_at':'2026-11-10T13:00:00Z'})
            old={('sv01-013','pokeball'):'2026-11-11T13:00:00Z',
                 ('sv01-013','normal'):'2026-11-09T10:00:00Z'}
            r=m.preserve_manual_scan_requests(q,old)
            self.assertEqual(r['preserved'],1)
            with q.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]['manual_scan_requested_at'],old[('sv01-013','pokeball')])
            self.assertEqual(rows[1]['manual_scan_requested_at'],'2026-11-10T13:00:00Z')
            self.assertEqual([x['needs_price'] for x in rows],['YES','NO'])
    def test_missing_manual_variant_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            q=Path(t)/'queue-de.csv'
            q.write_text('cardyssey_karte,variante_id,manual_scan_requested_at\nsv01-013,normal,\n')
            with self.assertRaises(RuntimeError):
                m.preserve_manual_scan_requests(q,{('sv01-013','masterball'):'2026-11-11T13:00:00Z'})
if __name__=='__main__':unittest.main()
