import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))

spec=importlib.util.spec_from_file_location(
    "cardmarket_full_map",Path(__file__).with_name("map-all-de-cardmarket-catalog.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FullCatalogMapTests(unittest.TestCase):
    def test_unique_exact_name_in_verified_expansion(self):
        names={("1","pikachu"):[{"idProduct":123,"idExpansion":1,"name":"Pikachu"}]}
        ids,status=module.candidates_for_card(
            {"set_id":"base1","english_name":"Pikachu"},names,{"base1":"1"})
        self.assertEqual((ids,status),(["123"],"SINGLE_SET_PRODUCT"))

    def test_multiple_distinct_products_not_assumed_unique(self):
        names={("1","pikachu"):[{"idProduct":123},{"idProduct":456}]}
        ids,status=module.candidates_for_card(
            {"set_id":"base1","english_name":"Pikachu"},names,{"base1":"1"})
        self.assertEqual((ids,status),(["123","456"],"MULTIPLE_SET_PRODUCTS"))

    def test_no_verified_expansion_rejects_same_name(self):
        names={("1","pikachu"):[{"idProduct":123}]}
        ids,status=module.candidates_for_card(
            {"set_id":"unknown","english_name":"Pikachu"},names,{"base1":"1"})
        self.assertEqual((ids,status),([],"SET_NOT_VERIFIED"))

    def test_expansion_mapping_requires_overlap(self):
        en=[{"set_id":"set-a","name":"A"},{"set_id":"set-a","name":"B"},{"set_id":"set-a","name":"C"}]
        products=[{"idExpansion":10,"name":"A"},{"idExpansion":10,"name":"B"},
                  {"idExpansion":10,"name":"C"},{"idExpansion":20,"name":"A"}]
        self.assertEqual(module.calculate_set_map(en,products),{"set-a":"10"})

if __name__=="__main__":unittest.main()
