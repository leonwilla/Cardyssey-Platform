import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("validator",Path(__file__).with_name("verify-reference-price-identity.py"))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ReferencePriceIdentityTests(unittest.TestCase):
 def test_stamped_card_cannot_inherit_generic_price(self):
  variant={"size":"standard","stamps":["winner"],"type":"holo"}
  evidence={"quotes":[{"locale":"en","amount":10,"basis":"ASKING","currency":"EUR","condition":None,"printing":None}]}
  status,reasons=module.classify(variant,evidence,"en")
  self.assertEqual("REQUIRES_IDENTITY_REVIEW",status)
  self.assertIn("STAMP_NOT_VERIFIED",reasons)
  self.assertIn("PRINTING_NOT_IDENTIFIED",reasons)
 def test_english_comparator_is_never_a_german_market_price(self):
  status,reasons=module.classify({"size":"standard"},{"origin_language":"en","quotes":[{"locale":"en","amount":100,"basis":"SOLD","currency":"EUR","condition":"NEAR_MINT","printing":"NORMAL"}]},"de")
  self.assertEqual("CROSS_LANGUAGE_REFERENCE",status)
  self.assertIn("ENGLISH_REFERENCE_NOT_GERMAN_PRICE",reasons)

 def test_missing_language_quote(self):
  status,reasons=module.classify({"size":"standard"},{"quotes":[{"locale":"de","amount":15,"basis":"SOLD","currency":"EUR","condition":"NEAR_MINT","printing":"NORMAL"}]},"en")
  self.assertIn("NO_LANGUAGE_QUOTE",reasons)
  self.assertNotEqual("READY_FOR_EXACT_PRICE_REVIEW",status)
 def test_jumbo_remains_unverified_without_jumbo_print(self):
  status,reasons=module.classify({"size":"jumbo"},{"quotes":[{"locale":"en","amount":15,"basis":"SOLD","currency":"EUR","condition":"NEAR_MINT","printing":"NORMAL"}]},"en")
  self.assertIn("SIZE_NOT_VERIFIED",reasons)
 def test_precise_sale_still_not_auto_published(self):
  status,reasons=module.classify({"size":"standard"},{"quotes":[{"locale":"en","amount":15,"basis":"SOLD","currency":"EUR","condition":"NEAR_MINT","printing":"NORMAL"}]},"en")
  self.assertEqual("READY_FOR_EXACT_PRICE_REVIEW",status)
  self.assertEqual([],reasons)

if __name__=="__main__":unittest.main()
