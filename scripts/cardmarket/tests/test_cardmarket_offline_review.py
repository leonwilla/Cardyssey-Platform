import importlib.util
import unittest
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "core"


def load(name):
    spec = importlib.util.spec_from_file_location(name, CORE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OfflineReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = load("resolve-multiple-search-hits")
        cls.offline = load("apply-cardmarket-offline-review")

    def test_base_unlimited_requires_empty_stamps(self):
        row = {"set_id":"base1", "sonderdruck":"unlimited", "stempel":"[]"}
        for subtype in ("unlimited", "unbegrenzt"):
            self.assertTrue(self.offline.is_unlimited({**row,"sonderdruck":subtype}))
        for attributes in ({"sonderdruck":"shadowless"}, {"stempel":'["1st-edition"]'}, {"foil":"cosmos"}):
            self.assertFalse(self.offline.is_unlimited({**row,**attributes}))

    def test_full_catalog_singleton_remains_a_card_only_reference(self):
        row = {"set_id":"sv07", "catalog_singleton_id":"70001", "catalog_expansion_id":"10",
               "sonderdruck":"", "stempel":'["test"]', "cardmarket_ids":"70001"}
        entry = {"error":self.offline.STAMP_REASON, "set_id":"sv07", "catalog_direct_id_verified":True,
                 "card_number_url_verified":True, "product_id":"70001",
                 "url":"https://www.cardmarket.com/en/Pokemon/Products/Singles/Stellar-Crown/A-SCR001"}
        products = {"70001":{"idExpansion":10, "idMetacard":17, "name":"A [Attack]"},
                    "70002":{"idExpansion":11, "idMetacard":17, "name":"A [Attack]"}}
        family = {"17":{"70001","70002"}}
        names = {self.offline.catalog_name(products["70001"]):{"70001","70002"}}
        # Verified other main sets are reprints. Unknown expansions could be a Prize Pack.
        self.assertEqual(self.offline.singleton_stamp(row,entry,products,family,names,{"10","11"}),
                         ("70001","Stellar-Crown/A-SCR001"))
        self.assertIsNone(self.offline.singleton_stamp(row,entry,products,family,names,{"10"}))
        self.assertIsNone(self.offline.singleton_stamp(row,{**entry,"card_number_url_verified":False},
                                                       products,family,names,{"10","11"}))

    def test_alternate_pages_use_exact_set_number_and_version(self):
        winner = "https://www.cardmarket.com/de/Pokemon/Products/Singles/Prismatic-Evolutions-Additionals/Leafeon-V2-xPRE005"
        key = ("sv08.5-005","variant")
        entry = {"card_id":key[0],"variant_id":key[1],"set_id":"sv08.5",
                 "score_top_candidate_urls":[winner,winner.replace("005","050"),
                   winner.replace("V2","V3"),winner.replace("/de/","/en/")]}
        queue = {key:{"set_id":"sv08.5","kartennummer":"005"}}
        result = self.resolver.resolve_set_version_candidates([entry],queue,{"sv08.5":"Prismatic-Evolutions"},"de")
        self.assertEqual(result,{key:[winner]})

    def test_historical_scope_uses_berlin_date(self):
        self.assertTrue(self.offline.historical_date("2026-11-09T23:05:00Z","2026-11-10"))
        self.assertFalse(self.offline.historical_date("2026-11-10T23:05:00Z","2026-11-10"))
