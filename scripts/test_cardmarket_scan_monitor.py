import csv,json,tempfile,unittest
from pathlib import Path
from scripts.cardmarket_scan_monitor import snapshot
class ScanMonitorTests(unittest.TestCase):
 def test_counts_deduplicate_and_do_not_mark_feed_scanned(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);rows=[{'cardyssey_karte':'a','variante_id':'v1','scan_tier':'2','needs_price':'YES'},
                   {'cardyssey_karte':'a','variante_id':'v2','scan_tier':'2','needs_price':'YES'},
                   {'cardyssey_karte':'b','variante_id':'v1','scan_tier':'4','needs_price':'NO'}]
   with (p/'queue-de.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
   with (p/'browser-observations-de.jsonl').open('w') as f:
    for x in [{'card_id':'a','variant_id':'v1','status':'ERROR'},{'card_id':'a','variant_id':'v1','status':'NO_EXACT_NUMBER_SEARCH_HIT'}]:f.write(json.dumps(x)+'\n')
   result=snapshot(p,'de');self.assertEqual(result['totalVariants'],3);self.assertEqual(result['uniqueCards'],2)
   self.assertEqual(result['browserTotal'],2);self.assertEqual(result['browserProcessed'],1)
   self.assertEqual(result['feedOnly'],1);self.assertEqual(result['problemCountInObserved'],1)
 def test_language_allowlist(self):
  with self.assertRaises(ValueError):snapshot(Path('.'),'other')
if __name__=='__main__':unittest.main()
