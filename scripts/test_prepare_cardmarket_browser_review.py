import unittest
import importlib.util
from pathlib import Path
_spec = importlib.util.spec_from_file_location("cardmarket_review", Path(__file__).with_name("prepare-cardmarket-browser-review.py"))
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
make_rows, triage = _module.make_rows, _module.triage


class ReviewTriageTests(unittest.TestCase):
    def example(self, **kwargs):
        row = {"set_code": "mep", "card_id": "mep-095", "variant_id": "legacy:holo",
               "english_name": "Lucario", "variant": {"type": "Holo"},
               "set_verified": True, "products": [{"id": 895610, "name": "Lucario"}],
               "unverified_identity_fields": ["LANGUAGE_UNVERIFIED"]}
        row.update(kwargs)
        return row

    def test_single_candidate_is_review_not_confirmed(self):
        row = make_rows([self.example()])[0]
        self.assertEqual(row["prioritaet"], "P2")
        self.assertEqual(row["status"], "ZU_PRUEFEN")
        self.assertFalse(row["manuell_bestaetigte_id"])

    def test_direct_external_id_is_prioritized_but_not_assigned(self):
        row = make_rows([self.example(exact_variant_provider_ids={"cardmarket": "895610"})])[0]
        self.assertEqual(row["prueffall"], "EXTERNAL_CARDMARKET_ID_IN_VERIFIED_SET")
        self.assertEqual(row["prioritaet"], "P1")
        self.assertEqual(row["manuell_bestaetigte_id"], "")

    def test_conflicting_direct_id_is_flagged(self):
        priority, action, _ = triage(self.example(exact_variant_provider_ids={"cardmarket": 123}))
        self.assertEqual((priority, action), ("P1", "EXTERNAL_CARDMARKET_ID_CONFLICT"))

    def test_stamped_single_candidate_not_simple_case(self):
        row = make_rows([self.example(variant={"type": "Holo", "stamps": ["Set-Logo"]})])[0]
        self.assertEqual(row["prioritaet"], "P3")

    def test_name_only_hints_never_become_candidates(self):
        row = make_rows([self.example(set_verified=False, products=[],
                      name_only_match_count=2, name_only_search_hints=[{"id": 123}])])[0]
        self.assertEqual(row["prueffall"], "NAME_ONLY_SEARCH_HINTS")
        self.assertEqual(row["produktkandidaten"], 0)
        self.assertEqual(row["namenstreffer_ids"], "123")

    def test_no_evidence_is_low_priority(self):
        self.assertEqual(triage(self.example(set_verified=False, products=[]))[0], "P5")

    def test_multiple_candidates(self):
        self.assertEqual(triage(self.example(products=[{"id": 1}, {"id": 2}]))[1], "MULTIPLE_SET_CANDIDATES")


if __name__ == "__main__":
    unittest.main()
