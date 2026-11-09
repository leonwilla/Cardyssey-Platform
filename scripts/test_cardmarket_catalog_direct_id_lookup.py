"""Regression checks for evidence-first Cardmarket product lookup."""
import csv,unittest
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parent
s=(ROOT/'cardmarket-language-browser-collector.ps1').read_text(encoding='utf-8-sig')
spec=spec_from_file_location('scan_failures',ROOT/'cardmarket-live-failures.py');m=module_from_spec(spec);spec.loader.exec_module(m)
class CatalogIdTests(unittest.TestCase):
 def test_queue_has_official_expansion_evidence_for_singleton(self):
  for lang in ('de','en'):
   p=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')/f'queue-{lang}.csv'
   with p.open(encoding='utf-8-sig') as f:
    r=csv.DictReader(f)
    self.assertIn('catalog_expansion_id',r.fieldnames)
    rows=[x for x in r if x['catalog_singleton_id']]
    self.assertGreater(len(rows),18000)
    self.assertTrue(all(x['catalog_expansion_id'].isdigit() for x in rows))
 def test_direct_result_requires_real_card_page_id_and_number(self):
  for marker in ('catalog_singleton_id','catalog_expansion_id',"$state.id -ne $directId",'sameNumber -and $sameSet','CARDMARKET_PROVIDER_CHALLENGE','NO_VERIFIED_REDIRECT_FALLBACK_TO_SEARCH'):
   self.assertIn(marker,s)
  self.assertIn('catalogIdLookupUnsupported=$true',s)
  self.assertIn('$landing.GetLeftPart([UriPartial]::Path)',s)
  self.assertIn("$out.catalog_direct_id_verified=$true",s)
 def test_direct_id_never_auto_proves_physical_print_or_price(self):
  branch=s.split("} elseif ($out.catalog_direct_id_verified -eq $true) {",1)[1].split('} elseif (',1)[0]
  self.assertIn('PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED',branch)
  self.assertNotIn('identity_confirmed = $true',branch)
  self.assertNotIn('median_all_offers_eur',branch)
 def test_print_review_requires_both_catalog_and_live_evidence(self):
  row={'catalog_singleton_id':'275420','catalog_expansion_id':'1607'}
  observed={'product_id':'275420','catalog_direct_id_verified':True}
  standard={**row,'set_id':'basep','kartennummer':'1','variante_id':'v1','drucktyp':'normal'}
  self.assertEqual(m.classify('PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED',observed,standard),'PREISPRUEFUNG')
  special={**standard,'stempel':'[\"grauer stern\"]'}
  self.assertEqual(m.classify('PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED',observed,special),'DRUCKPRUEFUNG')
  self.assertEqual(m.classify('PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED',{**observed,'product_id':'999999'},row),'ZUORDNUNG')
  self.assertEqual(m.classify('PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED',{**observed,'catalog_direct_id_verified':False},row),'ZUORDNUNG')
  self.assertEqual(m.classify('PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED',observed,{**row,'catalog_expansion_id':''}),'ZUORDNUNG')
if __name__=='__main__':unittest.main()
