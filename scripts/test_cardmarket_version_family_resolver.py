"""Version-page resolution must never turn a reprint candidate into a priced print."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
p=ROOT/'scripts/cardmarket-version-family-resolver.py'
spec=importlib.util.spec_from_file_location('cardmarket_version_family',p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def observed():
    def link(slug):
        return {'url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/'+slug+'?language=3',
                'text':slug}
    return {'href':'https://www.cardmarket.com/de/Pokemon/Cards/Joltik-Surprise-Attack/Versions',
            'challenge':False,'ready':'complete','heading':'Wattzapf - 3 versions',
            'anchors':[link('White-Flare/Joltik-V1-WHT033'),
                       link('White-Flare-Additionals/Joltik-V1-xWHT033'),
                       link('White-Flare-Additionals/Joltik-V2-xWHT033')]}

class VersionFamilyChecks(unittest.TestCase):
    def test_one_expansion_and_number_only_no_print_guess(self):
        x=mod.resolve_version_family(observed(),card_id='sv10.5w-033',
                  set_slug='White-Flare-Additionals',collector_suffix='xWHT033')
        self.assertEqual(x['totalVersionsObserved'],3)
        self.assertEqual(x['otherSetVersionsExcluded'],1)
        self.assertEqual([c['version'] for c in x['sameSetCardNumberCandidates']],['V1','V2'])
        self.assertFalse(x['safeToAutoPrice'])
        self.assertFalse(x['exactPrintVerified'])
        self.assertTrue(all(not v['productIdChecked'] and not v['priceVerified'] for v in x['sameSetCardNumberCandidates']))
    def test_id_requires_exact_live_product_page(self):
        obs=[{'url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/White-Flare-Additionals/Joltik-V1-xWHT033',
              'id':'836552','imgs':[{'src':'https://product-images.s3.cardmarket.com/51/xWHT/836552/836552.jpg'}]},
             {'url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/Scarlet-Violet/Joltik-V2-xWHT033',
              'id':'836551'}]
        catalog={'836552':{'idExpansion':6198,'idMetacard':450173},
                 '836551':{'idExpansion':6198,'idMetacard':450173}}
        x=mod.resolve_version_family(observed(),card_id='sv10.5w-033',
                 set_slug='White-Flare-Additionals',collector_suffix='xWHT033',
                 observations=obs,catalog=catalog)
        ids=[z['productId'] for z in x['sameSetCardNumberCandidates']]
        self.assertEqual(ids,['836552',None])
        self.assertTrue(x['sameSetCardNumberCandidates'][0]['imageUrl'].endswith('/836552/836552.jpg'))
        self.assertFalse(x['allCandidatesHaveCheckedProductId'])
    def test_challenge_wrong_host_and_wrong_family_rejected(self):
        x=observed();x['challenge']=True
        with self.assertRaises(ValueError):mod.resolve_version_family(x,card_id='x',set_slug='White-Flare',collector_suffix='WHT033')
        x=observed();x['href']='https://cardmarket.example/de/Pokemon/Cards/Joltik/Versions'
        with self.assertRaises(ValueError):mod.resolve_version_family(x,card_id='x',set_slug='White-Flare',collector_suffix='WHT033')
    def test_real_observations_21_and_11_expected(self):
        results=json.loads((ROOT/'config/cardmarket-version-family-evidence.json').read_text())
        for card,count,ids in [('sv01-013',21,{'689763','691000'}),('sv10.5w-033',11,{'836551','836552'})]:
            x=results[card]
            self.assertEqual(x['totalVersionsObserved'],count)
            self.assertEqual({p['productId'] for p in x['sameSetCardNumberCandidates']},ids)
            self.assertTrue(x['allCandidatesHaveCheckedProductId'])
            self.assertFalse(x['safeToAutoPrice'])
            self.assertTrue(all(p['imageUrl'].startswith('https://product-images.s3.cardmarket.com/') for p in x['sameSetCardNumberCandidates']))
    def test_admin_has_immutable_version_leads(self):
        src=(ROOT/'scripts/cardmarket-print-review-admin.py').read_text()
        self.assertIn('cardmarket-version-family-evidence.json',src)
        self.assertIn("family_observed.get('status')=='VERSION_FAMILY_PRINT_UNVERIFIED'",src)
        ui=(ROOT/'web/components/CardmarketReviewCard.tsx').read_text()
        self.assertIn('Drucktyp und Sprachpreis sind weiterhin unbestätigt',ui)

if __name__=='__main__':
    unittest.main()
