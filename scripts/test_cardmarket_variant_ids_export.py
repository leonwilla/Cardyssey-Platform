import csv,importlib.util,io,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('export',Path(__file__).with_name('export-cardmarket-full-queue.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class VariantIdExportTests(unittest.TestCase):
 def test_variant_id_precedes_name_wide_candidates(self):
  sql=m.SQL.format(language='de')
  self.assertIn("v.value->>'cardmarketProductId'",sql)
  self.assertIn("jsonb_array_length(c.provider_product_ids)=1",sql)
  self.assertNotIn('string_agg(DISTINCT pid',sql)
 def test_real_undaunted_houndoom_5_and_82_separated(self):
  p=Path('/tmp/cm-queue-new-de.csv')
  if not p.exists():self.skipTest('local verification export not available')
  with p.open(encoding='utf-8') as f:
   rows=[r for r in csv.DictReader(f) if r['cardyssey_karte'] in ('hgss3-5','hgss3-82')]
  self.assertEqual({r['cardmarket_ids'] for r in rows if r['cardyssey_karte']=='hgss3-5'},{'279258','371567'})
  self.assertEqual({r['cardmarket_ids'] for r in rows if r['cardyssey_karte']=='hgss3-82'},{'279335'})
 def test_human_verified_identity_wins(self):
  self.assertIn("r.verification_state='VERIFIED_PRODUCT_ID'",m.SQL)
if __name__=='__main__':unittest.main()
