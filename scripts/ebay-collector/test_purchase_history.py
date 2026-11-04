import unittest
from datetime import date
from unittest.mock import patch
from purchase_history import purchase_date,verified_transaction,audit_purchase_history,cached_or_fetch

CARD={'card_id':'sv01-188','name':'Trank','local_id':'188','denominator':198,'set_name':'Karmesin & Purpur'}
PARENT='Karten Zur Auswahl: Karmesin & Purpur Reverse Holo Pokémon Pokemon Karte DE NM'
ROW={'variant':'Artikel: 188/198 Trank','displayedPrice':'EUR 1,00','quantity':'1','purchasedAt':'23 Sep 2026, 12:47:57 MESZ'}

class PurchaseHistoryTests(unittest.TestCase):
 def test_parses_real_ebay_purchase_timestamp(self):
  self.assertEqual(purchase_date(ROW['purchasedAt']).date().isoformat(),'2026-09-23')
 def test_real_purchase_is_importable_and_has_stable_id(self):
  sale,reason=verified_transaction(ROW,'404434722071',CARD,PARENT)
  self.assertEqual(reason,'CONFIRMED')
  self.assertEqual((sale['price_eur'],sale['sold_date'],sale['source']),(1.0,'2026-09-23','EBAY_PURCHASE_HISTORY'))
  self.assertIn('Reverse Holo',sale['title'])
  self.assertEqual(sale['item_id'],verified_transaction(ROW,'404434722071',CARD,PARENT)[0]['item_id'])
 def test_action_offer_without_price_is_not_imported(self):
  card={'card_id':'sv01-067','name':'Waaty','local_id':'067','denominator':198}
  r={'variant':'Einzelkarte: 067/198 Waaty','displayedPrice':'Als Aktionsangebot verkauft','quantity':'1','purchasedAt':'11 Okt 2026, 23:39:41 MESZ'}
  self.assertEqual(verified_transaction(r,'125866062535',card,'Pokemon Karmesin & Purpur DE Einzelkarten zur Auswahl')[1],'NO_PAID_PRICE')
 def test_cannot_assume_wrong_selected_card_was_sold(self):
  row,reason=verified_transaction(ROW,'404434722071',{'card_id':'sv01-001','name':'Tannza','local_id':'001','denominator':198},PARENT)
  self.assertIsNone(row)
  self.assertEqual(reason,'OTHER_CARD')
 def test_no_buyer_information_and_no_listing_level_counter_in_observation(self):
  sale,reason=verified_transaction(ROW,'404434722071',CARD,PARENT)
  self.assertEqual(reason,'CONFIRMED')
  self.assertNotIn('buyer',sale)
  self.assertNotIn('username',sale)
  self.assertNotIn('102',sale['item_id'])
  self.assertEqual(sale['quantity'],1)
 def test_set_specific_guards_reject_other_expansion(self):
  card=CARD|{'set_id':'sv01'}
  self.assertEqual(verified_transaction(ROW,'404434722071',card,'Entwicklungen in Paldea DE Reverse Holo')[1],'SET_UNCLEAR')
  self.assertEqual(verified_transaction(ROW,'404434722071',card,PARENT)[1],'CONFIRMED')
  self.assertEqual(verified_transaction(ROW|{'variant':'188/198 Trank Normal'},'404434722071',card,PARENT)[1],'VARIANT_CONFLICT')
 def test_rejects_ambiguous_prices_date_set_language_condition(self):
  cases=[({'displayedPrice':'Als Aktionsangebot verkauft'},'NO_PAID_PRICE'),
         ({'displayedPrice':'EUR 1,00 bis EUR 3,00'},'NO_PAID_PRICE'),
         ({'purchasedAt':'nicht bekannt'},'INVALID_SALE_DATE'),
         ({'variant':'Artikel: 188/199 Trank'},'OTHER_CARD')]
  for change,expected in cases:
   self.assertEqual(verified_transaction(ROW|change,'404434722071',CARD,PARENT)[1],expected)
  self.assertEqual(verified_transaction(ROW,'404434722071',CARD,'Karmesin & Purpur EN')[1],'LANGUAGE_UNCLEAR')
  self.assertEqual(verified_transaction(ROW,'404434722071',CARD,'Trank DE NM')[1],'SET_UNCLEAR')
  self.assertEqual(verified_transaction(ROW,'404434722071',CARD,PARENT+' Damaged')[1],'CONDITION_NOT_NM')
 def test_purchase_from_tannza_search_is_attributed_to_trank(self):
  report={'rows':[{'item_id':'404434722071','title':PARENT,'price_eur':1.0}]}
  tannza={'card_id':'sv01-001','name':'Tannza','local_id':'001','denominator':198,'set_id':'sv01'}
  trank=CARD|{'set_id':'sv01'}
  cache={'404434722071':{'status':'VERIFIED_ROWS','transactions':[ROW]}}
  with patch('purchase_history.cached_or_fetch',return_value=cache):
   result=audit_purchase_history(report,tannza,[tannza,trank])
  self.assertEqual(result['purchaseHistoryAudit']['confirmed'],0)
  self.assertEqual(result['purchaseHistoryAudit']['cross_card_confirmed'],1)
  self.assertEqual(result['purchaseHistoryCrossCardSales'][0]['cardId'],'sv01-188')
  self.assertEqual(result['purchaseHistoryCrossCardSales'][0]['sale']['price_eur'],1.0)
 def test_cached_results_not_re_scraped_and_no_cross_card_import(self):
  report={'rows':[{'item_id':'404434722071','title':PARENT,'price_eur':1.0}]}
  cached={'404434722071':{'status':'VERIFIED_ROWS','transactions':[ROW]}}
  with patch('purchase_history.cached_or_fetch',return_value=cached) as call:
   result=audit_purchase_history(report,CARD)
   self.assertEqual(result['purchaseHistoryAudit']['confirmed'],1)
   self.assertEqual(result['rows'][-1]['price_eur'],1.0)
   self.assertEqual(result['rows'][-1]['source'],'EBAY_PURCHASE_HISTORY')
  wrong={'card_id':'sv01-001','name':'Tannza','local_id':'001','denominator':198}
  with patch('purchase_history.cached_or_fetch',return_value=cached):
   result=audit_purchase_history({'rows':report['rows'][:1]},wrong)
   self.assertEqual(result['purchaseHistoryAudit']['confirmed'],0)
   self.assertEqual(result['purchaseHistoryAudit']['not_this_card'],1)

if __name__=='__main__':unittest.main()
