import unittest
from scripts.market_condition_policy import classify_condition

class ConditionPolicyTest(unittest.TestCase):
 def test_absent_de_is_assumed_not_verified(self):
  for s in (None,'','   '):self.assertEqual(classify_condition(s,language='de'),'assumed_nm')
 def test_no_global_assumption(self):
  self.assertEqual(classify_condition(None,language='en'),'unknown')
 def test_explicit_nm(self):
  for s in ('Near Mint','NM','Mint','Neuwertig'):
   self.assertEqual(classify_condition(s,language='de'),'explicit_nm')
 def test_non_nm_is_excluded(self):
  for s in ('Played','Good','Damaged','Lightly Played','Excellent','Poor','LP','HP','gespielt'):
   self.assertEqual(classify_condition(s,language='de'),'rejected')
 def test_unknown_not_assumed(self):
  self.assertEqual(classify_condition('collector grade 7',language='de'),'unknown')
if __name__=='__main__':unittest.main()
