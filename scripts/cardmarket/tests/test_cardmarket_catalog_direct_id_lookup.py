"""Regression checks for evidence-first Cardmarket product lookup."""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv,unittest
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parents[2]
s=(source_path('cardmarket-language-browser-collector.ps1')).read_text(encoding='utf-8-sig')
spec=spec_from_file_location('scan_failures',source_path('cardmarket-live-failures.py'));m=module_from_spec(spec);spec.loader.exec_module(m)
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
 def test_direct_redirect_disabled_and_normal_search_uses_catalog_verification(self):
  # The legacy branch remains only for audit compatibility, permanently
  # gated by a true default. There is no idProduct redirect at runtime.
  self.assertIn('$catalogIdLookupUnsupported=$true',s)
  self.assertNotIn('$catalogIdLookupUnsupported=$false',s)
  self.assertIn('if(!$savedUrl -and !$catalogIdLookupUnsupported -and',s)
  self.assertIn("if (!(Move-To $searchUrl))",s)
  self.assertIn("$out.search_load_mode='BROWSER_NAVIGATION'",s)
  self.assertIn('catalog_singleton_id',s)
  self.assertIn('if ($pageProductId -eq [string]$case.catalog_singleton_id',s)
  self.assertIn("$candidateId = [string](Js 'document.querySelector",s)
 def test_direct_id_never_auto_proves_physical_print_or_price(self):
  branch=s.split("} elseif ($out.catalog_direct_id_verified -eq $true -and",1)[1].split('} elseif (',1)[0]
  self.assertIn('PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED',branch)
  self.assertNotIn('identity_confirmed = $true',branch)
  self.assertNotIn('median_all_offers_eur',branch)
  self.assertIn('exact_print_verified=$false',s)
  self.assertIn('expected_reverse_holo',s)
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
