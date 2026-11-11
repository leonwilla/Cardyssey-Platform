"""Live-feed grounded invariants for Felori SVI013 V1/V2 + special prints."""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv,hashlib,json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
FEED_URL='https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json'
FEED=Path('/home/tv/.local/state/cardyssey-queue/price-feeds')/(hashlib.sha256(FEED_URL.encode()).hexdigest()+'.json')
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
class FeloriVersionTests(unittest.TestCase):
 def test_v1_v2_belong_to_same_verified_physical_set_not_gem_pack(self):
  products={str(p['idProduct']):p for p in json.loads(FEED.read_text())['products']}
  overrides=json.loads((ROOT/'config/cardmarket-verified-set-overrides.json').read_text())
  self.assertEqual(overrides['sv01']['expansionId'],'5223')
  self.assertEqual({str(products[i]['idExpansion']) for i in ('689763','691000')},{'5223'})
  self.assertEqual(str(products['689763']['idMetacard']),str(products['691000']['idMetacard']))
  self.assertNotEqual(str(products['806289']['idExpansion']),'5223')
 def test_narrowly_allow_offer_filters_and_never_special_stamp_foil(self):
  spec=json.loads((ROOT/'config/cardmarket-known-print-page-hints.json').read_text())['sv01-013']
  self.assertEqual(spec['setSlug'],'Scarlet-Violet')
  for var in ('endfynwn4n10gzq','cm4kqul3x1bwlz1f'):
   x=spec['variants'][var]
   self.assertEqual(x['slug'],'Sprigatito-V1-SVI013')
   self.assertEqual(x['standardFilterProductId'],'689763')
   self.assertFalse(x['printVerified'])
  for var in ('curated:de:sv01:013:grass-stamp','curated:de:sv01:013:holo'):
   x=spec['variants'][var]
   self.assertFalse(x['printVerified'])
   self.assertNotIn('standardFilterProductId',x)
 def test_images_match_observed_product_ids(self):
  a=json.loads((ROOT/'config/cardmarket-verified-version-page-images.json').read_text())['sv01-013']
  for pid in ('689763','691000'):
   self.assertIn('/'+pid+'/'+pid+'.jpg',a[pid]['imageUrl'])
   self.assertTrue(a[pid]['imageUrl'].startswith('https://product-images.s3.cardmarket.com/51/SVI/'))
   self.assertIn(a[pid]['version'],('V1','V2'))
 def test_both_queues_keep_real_candidate_products_and_protect_special_prints(self):
  for lang in ('de','en'):
   with (BASE/f'queue-{lang}.csv').open(encoding='utf-8-sig') as f:
    rows={r['variante_id']:r for r in csv.DictReader(f) if r['cardyssey_karte']=='sv01-013'}
   for var in ('endfynwn4n10gzq','cm4kqul3x1bwlz1f'):
    self.assertEqual(rows[var]['catalog_singleton_id'],'689763')
    self.assertEqual(rows[var]['reference_standard_filter_supported'],'YES')
    self.assertEqual(rows[var]['reference_print_verified'],'NO')
   self.assertIn('691000',rows['endfynwn4n10gzq']['cardmarket_ids'])
   if lang=='de':
    for var in ('curated:de:sv01:013:grass-stamp','curated:de:sv01:013:holo'):
     self.assertEqual(rows[var]['reference_standard_filter_supported'],'NO')
     self.assertNotEqual(rows[var]['routing_state'],'VERIFIED_PRODUCT_ID')
 def test_weekly_refresh_persists_all_verified_set_expansions_before_page_hints(self):
  s=(source_path('run-cardmarket-identity-weekly.py')).read_text()
  self.assertIn('verified_expansion_repairs',s)
  self.assertIn('repair-cardmarket-verified-expansions.py',s)
  self.assertLess(s.index('repair-cardmarket-verified-expansions.py'),s.index('cardmarket-apply-print-page-hints.py'))
 def test_review_shows_both_product_images_not_one_guessed_stamp(self):
  s=(ROOT/'web/components/CardmarketReviewCard.tsx').read_text()
  self.assertIn('entry.version_product_images.map(v=>',s)
  self.assertIn('Sonderstempel und Holo-Muster sind dadurch noch nicht automatisch bestätigt',s)
  self.assertIn('Produktkandidat öffnen (Druck noch offen)',s)
 def test_no_implicit_print_pricing_from_standard_product_hint(self):
  s=(source_path('cardmarket-language-browser-collector.ps1')).read_text(encoding='utf-8-sig')
  self.assertIn("$out.standard_offer_filter_candidate=$true",s)
  self.assertIn("$out.exact_print_verified=$false",s)
  self.assertIn("$out.expected_reverse_holo",s)
  self.assertIn("$out.median_all_offers_eur=if($out.all_pages_complete)",s)
  self.assertIn("$out.status='PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED'",s)
if __name__=='__main__':unittest.main()
