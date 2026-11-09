import importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('manual',Path(__file__).with_name('cardmarket-manual-product-review.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ManualProductReviewTests(unittest.TestCase):
 def test_only_exact_cardmarket_domains_allowed(self):
  self.assertTrue(m.valid_link('https://www.cardmarket.com/de/Pokemon/Products/Singles/Set/Caterpie-V2-Z1'))
  self.assertTrue(m.valid_link('https://www.cardmarket.com/Pokemon/Products?idProduct=581845'))
  for u in ('http://www.cardmarket.com/Pokemon/Products?idProduct=123','https://cardmarket.com/Pokemon/Products?idProduct=123',
     'https://www.cardmarket.com.evil.org/Pokemon/Products?idProduct=123',
     'https://www.cardmarket.com/Pokemon/Products?idProduct=not_an_id',
     'https://www.cardmarket.com@evil.org/Pokemon/Products?idProduct=581845',
     'https://www.cardmarket.com/de/Pokemon/Products/Search?searchString=Raupy'):
   self.assertFalse(m.valid_link(u),u)
 def test_curated_variant_id_is_valid_and_wrong_foreign_set_is_rejected(self):
  # Real Cardyssey IDs contain colons; rejecting them before the browser
  # hid the actual issue: Gem Pack Chinese is not SV01 Scarlet-Violet.
  case={'language_code':'de','card_id':'sv01-013','variant_id':'curated:de:sv01:013:grass-stamp','set_id':'sv01'}
  with patch.object(m,'record',return_value=case),patch.object(m.subprocess,'run') as runner:
   with self.assertRaisesRegex(ValueError,'wrong_set_url_expected_Scarlet-Violet'):
    m.preview({'language':'de','cardId':'sv01-013','variantId':case['variant_id'],
      'url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/Gem-Pack-Vol-1/Sprigatito-V1-CBB1C01?isReverseHolo=Y'})
   runner.assert_not_called()
 def test_other_set_url_rejected_before_browser(self):
  case={'language_code':'de','card_id':'2019sm-1','variant_id':'a','set_id':'2019sm'}
  with patch.object(m,'record',return_value=case),patch.object(m.subprocess,'run') as runner:
   with self.assertRaisesRegex(ValueError,'wrong_set_url_expected_McDonalds-Collection-2019'):
    m.preview({'language':'de','cardId':'2019sm-1','variantId':'a','url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/Burning-Shadows/Caterpie-BUS1'})
   runner.assert_not_called()
 def test_mcDonalds_and_burning_shadows_are_separate_set_guards(self):
  import json
  guard=json.loads((Path('/home/tv/cardshop')/'config/cardmarket-set-url-guards.json').read_text())
  self.assertEqual(guard['2019sm'],'McDonalds-Collection-2019')
  self.assertEqual(guard['sm3'],'Burning-Shadows')
 def test_blocked_browser_never_creates_preview(self):
  case={'language_code':'de','card_id':'2019sm-1','variant_id':'a','matched_set_ids':['479679'],'set_id':'2019sm'}
  with tempfile.TemporaryDirectory() as td,patch.object(m,'STORE',Path(td)),patch.object(m,'record',return_value=case),patch.object(m.subprocess,'run') as run:
   run.return_value.returncode=1;run.return_value.stderr='CARDMARKET_PROVIDER_CHALLENGE'
   with self.assertRaisesRegex(ValueError,'cloudflare_blocked'):
    m.preview({'language':'de','cardId':'2019sm-1','variantId':'a','url':'https://www.cardmarket.com/Pokemon/Products?idProduct=479679'})
   self.assertEqual(list(Path(td).iterdir()),[])
 def test_preview_creates_untrusted_price_reference_and_explicit_conflict(self):
  case={'language_code':'de','card_id':'2019sm-1','variant_id':'a','matched_set_ids':['479679'],'set_id':'2019sm','provider_expansion_id':'3354','printed_number':'1','card_name':'Raupy','print_type':'Holo'}
  page={'id':'581845','url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/McDonalds-Collection-2019/Caterpie-V2','heading':'Caterpie','crumbs':['2019 McDonalds','Caterpie']}
  with tempfile.TemporaryDirectory() as td,patch.object(m,'STORE',Path(td)),patch.object(m,'record',return_value=case),patch.object(m,'catalog',side_effect=[{'581845':{'idExpansion':3354,'name':'Caterpie'}},{'581845':{'avg30':0.4}}]),patch.object(m.subprocess,'run') as run:
   run.return_value.returncode=0;run.return_value.stdout=json.dumps(page)
   result=m.preview({'language':'de','cardId':'2019sm-1','variantId':'a','url':'https://www.cardmarket.com/Pokemon/Products?idProduct=581845'})
   self.assertEqual(result['productId'],'581845')
   self.assertIsNone(result['languageSpecificPrice'])
   self.assertTrue(any('PRODUCT_NOT_IN_PREVIOUS_CANDIDATES' in w for w in result['warnings']))
   self.assertTrue((Path(td)/(result['token']+'.json')).exists())
 def test_confirm_requires_human_checkbox(self):
  with self.assertRaisesRegex(ValueError,'invalid_preview_token'):m.confirm({'token':'../escape','exactPrintConfirmed':True})
if __name__=='__main__':unittest.main()
