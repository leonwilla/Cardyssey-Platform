import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("validator",Path(__file__).with_name("price_identity_validation.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class IdentityTests(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual("8",module.normalize_number("008/102"))
        self.assertEqual("dp05",module.normalize_number("DP05"))
    def test_language_not_proven_by_catalogue_name(self):
        reasons=module.print_reasons({"type":"holo"},"Machamp",set_verified=True,number_verified=True)
        self.assertIn("LANGUAGE_UNVERIFIED",reasons)
        self.assertIn("EDITION_UNVERIFIED",reasons)
    def test_stamped_and_jumbo(self):
        reasons=module.print_reasons({"stamps":["winner"],"size":"jumbo"},"Marshtomp",
            language_verified=True,edition_verified=True,number_verified=True,set_verified=True)
        self.assertIn("STAMP_UNVERIFIED",reasons)
        self.assertIn("SIZE_UNVERIFIED",reasons)
    def test_unambiguous_is_not_sufficient(self):
        self.assertEqual("READY_FOR_REVIEW",module.candidate_status(1,["LANGUAGE_UNVERIFIED"]))
        self.assertEqual("AMBIGUOUS_PRODUCT_IDENTITY",module.candidate_status(2,[]))
    def test_wrong_set_name_match_never_becomes_price_candidate(self):
        matches=[{"idExpansion":10,"idProduct":1},{"idExpansion":20,"idProduct":2}]
        confirmed,hints=module.split_by_verified_expansion(matches,30)
        self.assertEqual([],confirmed)
        self.assertEqual(2,len(hints))
        confirmed,hints=module.split_by_verified_expansion(matches,20)
        self.assertEqual([2],[p["idProduct"] for p in confirmed])
        self.assertEqual([1],[p["idProduct"] for p in hints])
        confirmed,hints=module.split_by_verified_expansion(matches,None)
        self.assertEqual([],confirmed)
        self.assertEqual(2,len(hints))
    def test_explicit_print_evidence(self):
        self.assertEqual([],module.print_reasons({"stamps":["winner"],"size":"jumbo"},
            "Marshtomp Jumbo Winner",language_verified=True,edition_verified=True,
            number_verified=True,set_verified=True))
if __name__=="__main__":unittest.main()
