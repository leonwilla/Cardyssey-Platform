import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("cm_audit", Path(__file__).with_name("audit-cardmarket-variant-evidence.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AuditTests(unittest.TestCase):
    def row(self, **overrides):
        d = {"language": "de", "card_id": "x", "variant_id": "holo", "set_verified": True,
             "products": [{"id": 111}], "exact_variant_provider_ids": {"cardmarket": 111}}
        d.update(overrides)
        return d

    def test_matching_id_is_not_autoverified(self):
        rows, s = module.audit([self.row()])
        self.assertEqual(rows[0]["status"], "DIRECT_ID_SET_MATCH_REVIEW")
        self.assertEqual(s["fully_verified_prints"], 0)

    def test_conflict(self):
        self.assertEqual(module.classify(self.row(exact_variant_provider_ids={"cardmarket": 999})), "DIRECT_ID_CONFLICT_REVIEW")

    def test_name_hint_is_not_same_set(self):
        row = self.row(set_verified=False, products=[], exact_variant_provider_ids={}, name_only_search_hints=[{"id": 111}])
        self.assertEqual(module.classify(row), "NAME_ONLY_HINT_NOT_VERIFIED")

    def test_duplicate_key(self):
        with self.assertRaises(ValueError):
            module.audit([self.row(), self.row()])


if __name__ == "__main__": unittest.main()
