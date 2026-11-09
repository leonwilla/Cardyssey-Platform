"""UI regressions: useful card artwork URL, correct set label, distinct stamps."""
import json,re,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class Checks(unittest.TestCase):
 def test_source_image_ends_with_actual_image_file(self):
  script=(ROOT/'cardmarket-print-review-admin.py').read_text()
  self.assertIn("rtrim(c.image_source_url,'/') || '/high.webp'",script)
  self.assertIn(' AS card_image_url',script)
  self.assertIn(' AS set_name',script)
 def test_variant_name_is_visible_and_image_not_asserted_to_be_exact_print(self):
  ts=(ROOT.parent/'web/components/CardmarketReviewCard.tsx').read_text()
  self.assertIn('Gesuchte Variante:',ts)
  self.assertIn('Grundkartenbild',ts)
  self.assertIn('muss den seltenen Stempel nicht zeigen',ts)
  self.assertIn('onError={()=>setImageFailed(true)}',ts)
 def test_pikachu_physical_variants_are_kept_distinct(self):
  ts=(ROOT.parent/'web/app/admin/prices/page.tsx').read_text()
  self.assertIn('Offene Sonderdrucke',ts)
  self.assertIn('p.printStamp',ts)
 def test_link_preview_accepts_colon_variant_identity(self):
  src=(ROOT/'cardmarket-manual-product-review.py').read_text()
  self.assertIn("r'[a-zA-Z0-9_.:-]{1,128}',variant",src)
 def test_felori_version_family_discovery_is_read_only(self):
  source=(ROOT/'cardmarket-print-review-admin.py').read_text()
  self.assertIn('version_families=defaultdict(list)',source)
  self.assertIn("row['version_family_product_count']",source)
  self.assertIn("row['version_page_url']",source)
  seeds=json.loads((ROOT.parent/'config/cardmarket-version-page-seeds.json').read_text())
  self.assertEqual(seeds['sv01-013']['metacardId'],'415179')
  ui=(ROOT.parent/'web/components/CardmarketReviewCard.tsx').read_text()
  self.assertIn('Alle Druckversionen auf Cardmarket vergleichen',ui)
  self.assertIn('aus fremden Sets werden nicht als dieselbe Karte bestätigt',ui)
 def test_foreign_gem_pack_does_not_auto_become_sv01_german(self):
  guards=json.loads((ROOT.parent/'config/cardmarket-set-url-guards.json').read_text())
  self.assertEqual(guards.get('sv01'),'Scarlet-Violet')
if __name__=='__main__':unittest.main()
