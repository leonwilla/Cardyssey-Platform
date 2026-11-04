import unittest
from unittest.mock import Mock
from source_policy import is_bulk_rarity,ebay_required,load_bulk_ids
class SourceRoutingTests(unittest.TestCase):
 def test_bulk_only_common_and_uncommon(self):
  for value in ('Häufig','Ungewöhnlich','COMMON','uncommon','C','U','rare_c','rare_u_c','One Diamond','Deux Diamant'):
   self.assertTrue(is_bulk_rarity(value))
   self.assertFalse(ebay_required({'rarity':value}))
 def test_rare_and_special_stay_ebay_eligible(self):
  for value in ('Selten','Selten, Illustration','Selten, besondere Illustration','Doppelselten','Ultra Selten','Hyperselten',None):
   self.assertTrue(ebay_required({'rarity':value}))
 def test_bulk_ids_come_from_exact_german_catalog(self):
  db=Mock(return_value='sv01-001\nsv01-002')
  self.assertEqual(load_bulk_ids(db),{'sv01-001','sv01-002'})
  self.assertIn("language_code='de'",db.call_args.args[0])
if __name__=='__main__':unittest.main()
