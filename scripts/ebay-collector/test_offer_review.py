import unittest
from unittest.mock import patch
from offer_references import store_offer_candidates
from price_review_admin import change

class OfferReviewTests(unittest.TestCase):
 def test_selection_offer_is_recorded_without_sale_import(self):
  report={'rows':[{'item_id':'123456789012','title':'Pokemon Karmesin Purpur Einzelkarten zur Auswahl',
                   'url':'https://www.ebay.de/itm/123456789012','image_url':None,'price_eur':1.0},
                  {'item_id':'123456789013','title':'Tannza 001/198 Karmesin Purpur',
                   'url':'https://www.ebay.de/itm/123456789013','price_eur':3.0}]}
  with patch('offer_references.db') as db:
   self.assertEqual(store_offer_candidates(report,{'card_id':'sv01-001'}),1)
   self.assertIn('ebay_offer_reference',db.call_args.args[0])
   self.assertNotIn('ebay_sold_history',db.call_args.args[0])
 def test_generic_selection_titles_are_recognized(self):
  from offer_references import MULTI
  examples=('Pokemon Karten Karmesin und Purpur Set Einzelkarten Deutsch',
    'Pokemon Karmesin und Purpur SVI Near Mint Reverse + Holo DE Einzelkarten Sleeved',
    'Pokemon Karmesin und Purpur SVI DE Near Mint Einzelkarten zum aussuchen Sleeved')
  for title in examples:self.assertIsNotNone(MULTI.search(title))
  self.assertIsNone(MULTI.search('Tannza 001/198 Karmesin und Purpur Pokemon Karte Deutsch'))
 def test_finished_and_no_sale_are_fixed_refresh_periods(self):
  with patch('price_review_admin.db',side_effect=['1','']) as db:
   result=change('sv01-001','VERIFIED',30,True,'')
   self.assertEqual(result['refreshDays'],7)
   self.assertIn("'VERIFIED',7",db.call_args.args[0])
  with patch('price_review_admin.db',side_effect=['1','']) as db:
   result=change('sv01-001','NO_VERIFIED_SALE',7,True,'')
   self.assertEqual(result['refreshDays'],30)
   self.assertIn("'NO_VERIFIED_SALE',30",db.call_args.args[0])
 def test_review_validation_and_persistence(self):
  with patch('price_review_admin.db',side_effect=['1','']) as db:
   actual=change('sv01-001','NO_VERIFIED_SALE',14,True,'No confirmed sale')
   self.assertEqual(actual['refreshDays'],30)
   self.assertIn('ebay_card_review',db.call_args.args[0])
  for payload in [('OTHER',7,True),('AUTO',13,True),('AUTO',7,'maybe')]:
   with self.assertRaises(ValueError):change('sv01-001',*payload,'')

if __name__=='__main__':unittest.main()
