import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('review',source_path('cardmarket-print-review-admin.py'))
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class QueueSyncTests(unittest.TestCase):
 def test_identity_update_uses_exact_card_and_variant(self):
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory);cols=['cardyssey_karte','variante_id','cardmarket_ids','known_url','routing_state']
   rows=[dict(cardyssey_karte='x',variante_id=v,cardmarket_ids='123,456',known_url='https://www.cardmarket.com/old',routing_state='SOURCE_ONLY') for v in ('normal','reverse')]
   with (p/'queue-de.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
   self.assertTrue(mod.sync_queue_identity('de','x','reverse','456',p))
   with (p/'queue-de.csv').open(encoding='utf-8-sig',newline='') as f:out=list(csv.DictReader(f))
   self.assertEqual(out[0]['routing_state'],'SOURCE_ONLY')
   self.assertEqual(out[1]['routing_state'],'VERIFIED_PRODUCT_ID')
   self.assertEqual(out[1]['cardmarket_ids'],'456')
   self.assertEqual(out[1]['known_url'],'')
 def test_bad_language_refused(self):
  self.assertFalse(mod.sync_queue_identity('fr','x','v','12',Path('.')))
if __name__=='__main__':unittest.main()
