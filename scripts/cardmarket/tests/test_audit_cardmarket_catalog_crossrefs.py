import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("cm_crossrefs", source_path("audit-cardmarket-catalog-crossrefs.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class CrossRefs(unittest.TestCase):
    def test_same_metacard_different_set_not_approved(self):
        cases = [{"language": "de", "card_id": "x", "variant_id": "v", "exact_variant_provider_ids": {"cardmarket": 2}, "products": [{"id": 1}]}]
        products = [{"idProduct": 1, "idExpansion": 10, "idMetacard": 5}, {"idProduct": 2, "idExpansion": 20, "idMetacard": 5}]
        results, summary = module.crosscheck(cases, products)
        self.assertEqual(results[0]["crossref_status"], "SAME_METACARD_DIFFERENT_PRODUCT_OR_EXPANSION")
        self.assertFalse(results[0]["safe_to_assign_product_id"])
        self.assertEqual(summary["automatically_assigned"], 0)

    def test_same_product_still_requires_print_review(self):
        cases = [{"exact_variant_provider_ids": {"cardmarket": 2}, "products": [{"id": 2}]}]
        result, _ = module.crosscheck(cases, [{"idProduct": 2, "idExpansion": 20}])
        self.assertEqual(result[0]["crossref_status"], "DIRECT_ID_IN_SET_REVIEW_PRINT")
        self.assertFalse(result[0]["safe_to_assign_product_id"])

    def test_missing_direct_id(self):
        result, _ = module.crosscheck([{"products": []}], [])
        self.assertEqual(result[0]["crossref_status"], "NO_DIRECT_VARIANT_ID")

    def test_direct_not_in_catalog(self):
        result, _ = module.crosscheck([{"exact_variant_provider_ids": {"cardmarket": 12345}}], [])
        self.assertEqual(result[0]["crossref_status"], "DIRECT_ID_NOT_IN_CURRENT_CATALOG")

if __name__ == "__main__": unittest.main()
