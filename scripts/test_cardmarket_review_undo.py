import csv,importlib.util,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('review',Path(__file__).with_name('cardmarket-print-review-admin.py'))
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
class UndoTests(unittest.TestCase):
 def test_queue_undo_restores_candidate_without_touching_price(self):
  with tempfile.TemporaryDirectory() as td:
   base=Path(td);p=base/'queue-de.csv';cols=['cardyssey_karte','variante_id','routing_state','cardmarket_ids','known_url','manual_scan_requested_at']
   with p.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerow(dict(zip(cols,['2019sm-1','v1','VERIFIED_PRODUCT_ID','777777','https://www.cardmarket.com/de/Pokemon/Products/Singles/Wrong','2026-11-09T12:00:00Z'])))
   self.assertTrue(review.revert_queue_identity('de','2019sm-1','v1',['412849'],base))
   with p.open() as f:r=next(csv.DictReader(f))
   self.assertEqual(r['cardmarket_ids'],'412849')
   self.assertEqual(r['routing_state'],'UNVERIFIED')
   self.assertEqual(r['known_url'],'')
   self.assertEqual(r['manual_scan_requested_at'],'')
 def test_already_pending_case_cannot_be_undone(self):
  with patch.object(review,'pg',return_value='{"undone":0,"routeRemoved":0,"candidateIds":null}'):
   with self.assertRaisesRegex(ValueError,'no_review_decision_to_undo'):
    review.undo_case({'language':'de','cardId':'2019sm-1','variantId':'jr7oetx1mqug9'})
if __name__=='__main__':unittest.main()
