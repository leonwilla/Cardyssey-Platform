import unittest
from scripts.cardmarket_variant_recheck import candidate_audit
class VariantRecheckTests(unittest.TestCase):
 def setUp(self):
  self.products={'479679':{'idMetacard':226279},'581845':{'idMetacard':226279}}
  self.row={'matched_set_ids':'479679,581845','classification':'MULTIPLE_PRODUCTS_IN_VERIFIED_SET'}
 def test_user_supplied_link_is_separate_manual_review_not_verified_price(self):
  row={'matched_set_ids':'412849','classification':'ONE_PRODUCT_IN_VERIFIED_SET'}
  x=candidate_audit(row,{'412849':{'idExpansion':2829}},None,user_reference_url='https://www.cardmarket.com/de/Pokemon/Products/Singles/McDonalds-Collection-2019/Caterpie-MCD191')
  self.assertEqual(x['category'],'MANUAL_COMPARISON_READY')
  self.assertFalse(x['printVerified'])
  self.assertFalse(x['priceApproved'])
 def test_without_matching_version_proof_is_automatic(self):
  x=candidate_audit(self.row,self.products,None)
  self.assertEqual(x['category'],'AUTO_VERSION_DISCOVERY')
  self.assertEqual(x['languageAvailability'],'UNKNOWN_NOT_PROVEN_ABSENT')
  self.assertFalse(x['printVerified'])
 def test_observed_version_does_not_certify_holo(self):
  obs={'url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/McDonalds-Collection-2019-2/Caterpie-V2-MCD19F2?language=3',
   'product_id':'581845','identity_confirmed':True,'status':'FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE',
   'verified_lang_nm_offers':2}
  x=candidate_audit(self.row,self.products,obs)
  self.assertEqual(x['versionObserved'],'V2')
  self.assertEqual(x['category'],'MANUAL_COMPARISON_READY')
  self.assertEqual(x['languageAvailability'],'OFFERS_OBSERVED')
  self.assertFalse(x['printVerified'])
 def test_zero_offers_never_means_language_does_not_exist(self):
  obs={'url':'https://www.cardmarket.com/en/Pokemon/Products/Singles/Set/Caterpie-V1-Z1',
  'product_id':'479679','identity_confirmed':True,'status':'FILTER_UNVERIFIED_EMPTY','verified_lang_nm_offers':0}
  x=candidate_audit(self.row,self.products,obs)
  self.assertEqual(x['languageAvailability'],'UNKNOWN_NOT_PROVEN_ABSENT')
 def test_wrong_product_id_version_is_not_proof(self):
  obs={'url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/Set/Caterpie-V2-Z1',
  'product_id':'111111','identity_confirmed':True,'status':'FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE','verified_lang_nm_offers':1}
  x=candidate_audit(self.row,self.products,obs)
  self.assertEqual(x['category'],'AUTO_VERSION_DISCOVERY')
  self.assertIsNone(x['versionObserved'])
if __name__=='__main__':unittest.main()
