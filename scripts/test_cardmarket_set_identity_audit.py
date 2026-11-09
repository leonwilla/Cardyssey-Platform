import unittest
import importlib.util,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
spec=importlib.util.spec_from_file_location('audit',Path(__file__).with_name('cardmarket-set-identity-audit.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assess=m.assess
class SetIdentityAuditTests(unittest.TestCase):
 def test_identical_reprints_are_ambiguous_not_automatically_wrong(self):
  names=['Caterpie','Pikachu','Eevee']
  expansions={'2829':{'caterpie':1,'pikachu':1,'eevee':1},'3354':{'caterpie':1,'pikachu':1,'eevee':1}}
  x=assess(names,'2829',expansions)
  self.assertEqual(x['status'],'AMBIGUOUS_OVERLAPPING_EXPANSIONS')
 def test_unique_matching_expansion_not_flagged(self):
  names=['A','B','C','D']
  x=assess(names,'42',{'42':{'a':1,'b':1,'c':1,'d':1},'44':{'a':1}})
  self.assertEqual(x['status'],'NO_STRONG_CONFLICT_FOUND')
 def test_bad_existing_choice_flagged_without_reassigning_it(self):
  names=['A','B','C','D','E','F']
  x=assess(names,'42',{'42':{'a':1},'44':{'a':1,'b':1,'c':1,'d':1,'e':1,'f':1}})
  self.assertEqual(x['status'],'SELECTED_EXPANSION_NEEDS_REVIEW')
  self.assertEqual(x['top'][0]['expansionId'],'44')
if __name__=='__main__':unittest.main()
