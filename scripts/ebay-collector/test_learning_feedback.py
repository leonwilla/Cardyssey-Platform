import unittest
from unittest.mock import patch
from learning_feedback import record,DECISIONS

class LearningFeedbackTests(unittest.TestCase):
 def test_human_examples_are_saved_only_to_feedback_table(self):
  with patch('learning_feedback.db',side_effect=['1','']) as db:
   result=record('sv01-001','123456789012','VALID_SINGLE_SALE','Exact print and paid price','Tannza 001/198')
   self.assertTrue(result['saved'])
   self.assertFalse(result['affectsPrice'])
   sql=db.call_args.args[0]
   self.assertIn('ebay_listing_feedback',sql)
   self.assertNotIn('ebay_sold_history',sql)
   self.assertNotIn('ebay_price_cache',sql)
 def test_no_untrusted_status_or_identity(self):
  for card,item,decision in [('sv01-001','123456789012','REWRITE_PRICE'),
      ('sv01-001;drop','123456789012','OTHER'),('sv01-001','random','OTHER')]:
   with self.assertRaises(ValueError):record(card,item,decision,'','')
 def test_all_explanations_have_defined_categories(self):
  self.assertTrue({'WRONG_CARD','VALID_SINGLE_SALE','MULTI_SELECTION','WRONG_VARIANT','PAID_PRICE_UNKNOWN','OTHER'}<=DECISIONS)

if __name__=='__main__':unittest.main()
