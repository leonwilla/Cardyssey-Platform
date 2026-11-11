import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))

spec=importlib.util.spec_from_file_location(
    "cardmarket_full_map",source_path("map-all-de-cardmarket-catalog.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FullCatalogMapTests(unittest.TestCase):
    def test_unique_exact_name_in_verified_expansion(self):
        names={("1","pikachu"):[{"idProduct":123,"idExpansion":1,"name":"Pikachu"}]}
        ids,status=module.candidates_for_card(
            {"set_id":"base1","english_name":"Pikachu"},names,{"base1":"1"})
        self.assertEqual((ids,status),(["123"],"SINGLE_SET_PRODUCT"))

    def test_full_set_overlap_tie_does_not_choose_wrong_expansion(self):
        en=[{'set_id':'2019sm','name':n} for n in ('Caterpie','Pikachu','Eevee')]
        products=[{'idExpansion':2829,'name':n} for n in ('Caterpie','Pikachu','Eevee')]
        products += [{'idExpansion':3354,'name':n} for n in ('Caterpie','Pikachu','Eevee')]
        self.assertNotIn('2019sm',module.calculate_set_map(en,products))

    def test_set_consensus_uses_distinct_variant_product_ids_not_names(self):
        products=[{'idProduct':100+i,'idExpansion':42,'name':'Houndoom'} for i in range(10)]
        products += [{'idProduct':200+i,'idExpansion':99,'name':'Houndoom'} for i in range(10)]
        cards=[{'set_id':'hgss3','card_id':f'hgss3-{i}','name':'Houndoom',
                'variants':[{'cardmarketProductId':100+i}]} for i in range(10)]
        self.assertEqual(module.calculate_variant_set_consensus(cards,products),{'hgss3':'42'})
    def test_split_name_same_set_has_no_automatic_print_identity(self):
        cards=[{'set_id':'hgss3','card_id':'hgss3-5','local_id':'5','name':'Houndoom'},
               {'set_id':'hgss3','card_id':'hgss3-82','local_id':'82','name':'Houndoom'}]
        number_sets=__import__('collections').defaultdict(set)
        for card in cards:number_sets[(card['set_id'],module.sem_name(card['name']))].add(card['local_id'])
        self.assertEqual(len(number_sets[('hgss3','houndoom')]),2)
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
