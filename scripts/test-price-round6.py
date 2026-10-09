#!/usr/bin/env python3
"""Identity, listing quality and atomic history regressions for western leftovers."""
import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("western", Path(__file__).with_name("resolve-cardtrader-western-safe.py"))
western = importlib.util.module_from_spec(spec)
spec.loader.exec_module(western)


class WesternTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(card_id="test", language_code="en", set_id="tk-xy-b", local_id="12", name="Bidoof",
                        variant_id="generated", legacy_variant="NORMAL", old_image="image", old_updated="2026-10-09T10:00:00Z",
                        variant=dict(id="generated", type="normal", size="standard", legacyVariant="NORMAL", stamps=[]))
        self.b = dict(id=10, game_id=5, category_id=73, expansion_id=1945, name="Bidoof",
                      version="Non-Holo | Trainer Kit 12/30", fixed_properties=dict(collector_number="12/30"),
                      tcg_player_id=20)
        self.p = dict(blueprint_id=10, graded=False, bundle_size=1, quantity=2,
                      price=dict(cents=160, currency="EUR"),
                      properties_hash=dict(signed=False, altered=False, pokemon_language="en", condition="Near Mint"))

    def match(self):
        return western.match_blueprint(self.row, [self.b], 1945)

    def test_exact_identity(self):
        self.assertIsNone(self.match()[1])
        self.assertEqual(western.Decimal("1.6"), western.listing_amount(self.p, 10))

    def test_unique_number_without_name_is_insufficient(self):
        self.b["name"] = "Pikachu"
        self.assertIsNone(self.match()[0])

    def test_wrong_expansion_category_game_number_rejected(self):
        for key, value in [("expansion_id", 1946), ("game_id", 1), ("category_id", 74)]:
            self.setUp(); self.b[key] = value
            self.assertIsNone(self.match()[0])
        self.setUp(); self.b["fixed_properties"]["collector_number"] = "13/30"
        self.assertIsNone(self.match()[0])

    def test_holo_cannot_price_normal_or_unlabelled_printing(self):
        for version in ["Holo Promo | BW78", "MEP 104", "Non-Holo | Winner 12/30", "Non-Holo | First Edition 12/30"]:
            self.b["version"] = version
            self.assertIsNone(self.match()[0])

    def test_duplicate_blueprint_is_ambiguous(self):
        self.assertIsNone(western.match_blueprint(self.row, [self.b, copy.deepcopy(self.b)], 1945)[0])

    def test_special_catalog_variant_or_other_language_rejected(self):
        for key, value in [("stamps", ["winner"]), ("foil", "cosmos"), ("subtype", "unlimited"), ("size", "jumbo")]:
            self.setUp(); self.row["variant"][key] = value
            self.assertIsNone(self.match()[0])
        self.setUp(); self.row["language_code"] = "de"
        self.assertIsNone(self.match()[0])

    def test_language_and_condition_must_be_explicit(self):
        for key, value in [("pokemon_language", ""), ("pokemon_language", "de"),
                           ("condition", "Slightly Played"), ("condition", "")]:
            self.setUp(); self.p["properties_hash"][key] = value
            self.assertIsNone(western.listing_amount(self.p, 10))

    def test_signed_altered_graded_reverse_or_unknown_rejected(self):
        for key, value in [("signed", True), ("altered", True), ("signed", None), ("reverse", True)]:
            self.setUp(); self.p["properties_hash"][key] = value
            self.assertIsNone(western.listing_amount(self.p, 10))
        self.setUp(); self.p["graded"] = True
        self.assertIsNone(western.listing_amount(self.p, 10))

    def test_bundle_stock_noninteger_currency_and_wrong_blueprint_rejected(self):
        for key, value in [("bundle_size", 2), ("quantity", 0), ("quantity", "1"), ("blueprint_id", 11)]:
            self.setUp(); self.p[key] = value
            self.assertIsNone(western.listing_amount(self.p, 10))
        for key, value in [("cents", True), ("cents", 1.5), ("currency", "USD")]:
            self.setUp(); self.p["price"][key] = value
            self.assertIsNone(western.listing_amount(self.p, 10))

    def test_tcgcsv_exact_product_printing_market_statistic(self):
        prices = [dict(productId=20, subTypeName="Normal", marketPrice=2, midPrice=9)]
        self.assertEqual(western.Decimal("1.8"), western.tcgcsv_amount(self.row, self.b, prices, western.Decimal(".9")))
        for change in [dict(productId=21), dict(subTypeName="Holofoil"), dict(marketPrice=None), dict(marketPrice="NaN")]:
            p = prices[0] | change
            self.assertIsNone(western.tcgcsv_amount(self.row, self.b, [p], western.Decimal(".9")))
        self.assertIsNone(western.tcgcsv_amount(self.row, self.b, prices * 2, western.Decimal(".9")))

    def test_invalid_or_duplicate_updates_cannot_write(self):
        u = dict(row=self.row, source="CARDTRADER_MARKETPLACE", base_eur="1.7391", detail="fixture")
        with patch.object(western.retail, "db") as db:
            for updates in [[u, u], [u | dict(source="OTHER")], [u | dict(base_eur="NaN")]]:
                with self.assertRaises(ValueError):
                    western.apply_updates(updates)
            db.assert_not_called()


def postgres_tests():
    case = WesternTests(); case.setUp()
    u = dict(row=case.row, source="CARDTRADER_MARKETPLACE", base_eur="1.7391", detail="fixture")
    setup = """
    CREATE TEMP TABLE catalog_cards_mirror(card_id text,language_code text,set_id text,local_id text,name text,variants jsonb,image_source_url text);
    CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,legacy_variant text,source text,
      base_eur numeric,updated_at timestamptz,resolution_status text,failure_detail text,next_attempt_at timestamptz);
    CREATE TEMP TABLE tcg_price_history(card_id text,language_code text,variant_id text,source text,base_eur numeric,captured_at timestamptz);
    INSERT INTO catalog_cards_mirror VALUES('test','en','tk-xy-b','12','Bidoof',""" + western.retail.quote(json.dumps([case.row["variant"]])) + """::jsonb,'image');
    INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,updated_at,resolution_status)
      VALUES('test','en','generated','NORMAL','2026-10-09T10:00:00Z','NO_PRICE');
    """
    scenarios = [
        ("success", "", [dict(prices=1, history=1)]),
        ("repeat", "", [dict(prices=1, history=1), dict(prices=0, history=0)]),
        ("newer_price", "UPDATE tcg_price_cache SET updated_at='2026-10-09T11:00:00Z',base_eur=99,resolution_status='PRICE_FOUND';", [dict(prices=0, history=0)]),
        ("changed_number", "UPDATE catalog_cards_mirror SET local_id='13';", [dict(prices=0, history=0)]),
        ("changed_variant", "UPDATE catalog_cards_mirror SET variants='[]';", [dict(prices=0, history=0)]),
        ("changed_timestamp", "UPDATE tcg_price_cache SET updated_at='2026-10-09T11:00:00Z';", [dict(prices=0, history=0)]),
        ("changed_image", "UPDATE catalog_cards_mirror SET image_source_url='different';", [dict(prices=0, history=0)]),
        ("changed_legacy", "UPDATE tcg_price_cache SET legacy_variant='HOLO';", [dict(prices=0, history=0)]),
        ("deleted_target", "DELETE FROM tcg_price_cache;", [dict(prices=0, history=0)]),
    ]
    for label, mutation, expected in scenarios:
        queries = western.apply_sql([u]) * len(expected)
        query = "BEGIN; SET LOCAL statement_timeout='15s';" + setup + mutation + queries
        query += "SELECT jsonb_build_object('history_count',COUNT(*)) FROM tcg_price_history; ROLLBACK;"
        r = subprocess.run(["docker", "exec", "-i", "cardyssey-db", "psql", "-U", "cardyssey", "-d", "cardyssey",
                            "-X", "-qAt", "-v", "ON_ERROR_STOP=1"], input=query, text=True, capture_output=True, timeout=25)
        if r.returncode:
            raise AssertionError(label + ": " + r.stderr)
        results = [json.loads(line) for line in r.stdout.splitlines() if line.startswith("{")]
        assert results[:-1] == expected, (label, results)
        assert results[-1]["history_count"] == sum(e["history"] for e in expected), (label, results)
    print("9 PostgreSQL rollback scenarios passed")
    conflict_spec = importlib.util.spec_from_file_location("conflicts", Path(__file__).with_name("audit-catalog-identity-conflicts.py"))
    conflict = importlib.util.module_from_spec(conflict_spec); conflict_spec.loader.exec_module(conflict)
    sql = """
    BEGIN; SET LOCAL statement_timeout='15s';
    CREATE TEMP TABLE catalog_cards_mirror(card_id text,language_code text,set_id text,local_id text,
      raw_payload jsonb,image_source_url text,variants jsonb,details_complete boolean);
    INSERT INTO catalog_cards_mirror VALUES
      ('official_same','ja','SV9','001','{"name":"ヒスイ ジュナイパー"}','image','[]',true),
      ('same','ja','SV9','1','{"name":"ヒスイジュナイパー"}','image','[{"id":"normal"}]',true),
      ('official_name','ja','SV9','002','{"name":"Correct"}','image','[]',true),
      ('name','ja','SV9','2','{"name":"Wrong"}','image','[{"id":"normal"}]',true),
      ('official_image','ko','SV9','003','{"name":"Same"}','official-image','[]',true),
      ('image','ko','SV9','3','{"name":"Same"}','provider-image','[{"id":"normal"}]',true),
      ('official_both','zh-tw','SV9','004','{"name":"Correct"}','official-image','[]',true),
      ('both','zh-tw','SV9','4','{"name":"Wrong"}','provider-image','[{"id":"normal"}]',true),
      ('official_cross','ja','SV9','005','{"name":"Correct"}','image','[]',true),
      ('cross','ko','SV9','5','{"name":"Wrong"}','image','[{"id":"normal"}]',true),
      ('official_digital','ja','A1','006','{"name":"Correct"}','image','[]',true),
      ('digital','ja','A1','6','{"name":"Wrong"}','image','[{"id":"normal"}]',true);
    """ + conflict.REPORT_SQL + "ROLLBACK;"
    r = subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey",
                        "-X","-qAt","-v","ON_ERROR_STOP=1"],input=sql,text=True,capture_output=True,timeout=25)
    assert r.returncode == 0, r.stderr
    report = json.loads(r.stdout.strip())
    assert len(report["samples"]) == 3, report
    assert {x["review_reason"] for x in report["samples"]} == {
        "name_differs_same_image","image_differs_same_name","name_and_image_differ"}, report
    assert report["automatic_repairs"] == 0
    print("Catalogue conflict fixture passed: whitespace, language and digital exclusions")



if __name__ == "__main__":
    if "--postgres" in sys.argv:
        postgres_tests()
    else:
        unittest.main()
