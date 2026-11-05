import unittest
from scripts.cardmarket_offer_median import evaluate

def example():
 return {'expected':{'language':'de','cardmarket_product_id':'273710','finish':'holo','first_edition':False},
  'pagination':{'all_pages_fetched':True,'capped':False,'total_offers':3},'offers':[
  {'id':str(i),'product_id':'273710','language':'de','finish':'holo','first_edition':False,
    'signed':False,'altered':False,'graded':False,'price_eur':p,'condition':c}
  for i,p,c in [(1,'83.43','NM'),(2,'89.00',None),(3,'95.00','PL')]]}
class TestOffers(unittest.TestCase):
 def test_missing_condition_is_flagged(self):
  result=evaluate(example());self.assertEqual(result['median_eur'],'86.22');self.assertEqual(result['assumed_nm'],1);self.assertFalse(result['safe_to_auto_publish'])
 def test_all_exact_explicit_allows_publish(self):
  d=example();d['offers'][1]['condition']='Near Mint';d['pagination']['total_offers']=3
  result=evaluate(d);self.assertTrue(result['safe_to_auto_publish']);self.assertEqual(result['accepted'],2)
 def test_unverified_pagination_not_full_market_median(self):
  d=example();d['pagination']['capped']=True
  self.assertEqual(evaluate(d)['status'],'PARTIAL_SAMPLE_MEDIAN_NOT_MARKET_WIDE')
 def test_missing_language_not_assumed(self):
  d=example();d['offers'][0].pop('language');self.assertEqual(evaluate(d)['accepted'],1)
 def test_mixed_editions_rejected(self):
  d=example();d['offers'][0]['first_edition']=True;self.assertEqual(evaluate(d)['accepted'],1)
 def test_bad_product_does_not_match(self):
  d=example();d['offers'][0]['product_id']='3';self.assertEqual(evaluate(d)['accepted'],1)
 def test_invalid_expected_rejected(self):
  d=example();d['expected']['finish']='unknown'
  with self.assertRaises(ValueError):evaluate(d)
if __name__=='__main__':unittest.main()
