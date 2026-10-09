#!/usr/bin/env python3
"""Negative identity/variant/price checks for the two new Korean retail sources."""
import copy
import json
import subprocess
import importlib.util
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

shop = load("resolve-shopify-ko-prices")


class ShopifyTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(card_id="official_ko_fixture", language_code="ko", identity_count=1,
                        set_id="S12a", local_id="121", rarity="C", german_species="Bidiza", native_name="비버니")
        options = [dict(name=name, position=i, values=[value]) for i, (name,value) in enumerate(
            [("Language","Korean"),("Condition","Near Mint"),("Edition","Normal")],1)]
        v = dict(id=2,option1="Korean",option2="Near Mint",option3="Normal",sku="s12a121-687683",
                 available=True,price="0.99")
        self.feed = dict(id=1,title="Bidoof - VSTAR Universe (Fixed) [s12a-121]", product_type="Pokémon Single",
                         options=options,variants=[v])
        self.detail = copy.deepcopy(self.feed)
        self.detail.update(type="Pokémon Single",url="/products/bidoof")
        self.detail["variants"][0].update(price=99,quantity_rule=dict(min=1,increment=1,max=None),
                                          quantity_price_breaks=[],selling_plan_allocations=[],requires_selling_plan=False)
        self.url = "https://manamarket.eu/products/bidoof"
        self.ld = dict(url=self.url,offers=[dict(url=self.url+"?variant=2",sku=v["sku"],price=.99,
                                                priceCurrency="EUR",availability="http://schema.org/InStock")])
        self.names = [{"9":"Bidoof","6":"Bidiza","3":"비버니"},{"9":"Pikachu","6":"Pikachu","3":"피카츄"}]

    def match(self,currency="EUR"):
        return shop.match_offer(self.row,self.feed,self.detail,self.ld,self.url,shop.SHOPS["mana"],self.names,currency)

    def test_explicit_exact_nm_korean_offer(self):
        o,r=self.match();self.assertIsNone(r);self.assertEqual("0.99",o["amount"])
        self.assertEqual("WEB_MANA_KO",o["source"])
        self.assertEqual("Near Mint",o["condition"])

    def test_wrong_or_ambiguous_catalog_identity(self):
        for key,value in [("language_code","ja"),("identity_count",2),("card_id","S12a-121")]:
            self.setUp();self.row[key]=value;self.assertEqual("catalog_identity",self.match()[1])

    def test_wrong_set_number_species_and_sku(self):
        for title in ["Bidoof - VSTAR Universe (Fixed) [s12b-121]","Bidoof - VSTAR Universe (Fixed) [s12a-122]",
                      "Pikachu - VSTAR Universe (Fixed) [s12a-121]"]:
            self.setUp();self.detail["title"]=title;self.assertIsNotNone(self.match()[1])
        self.setUp();self.detail["variants"][0]["sku"]="s12a122-687683"
        self.assertIsNotNone(self.match()[1])
        self.setUp();self.row["native_name"]="피카츄";self.assertEqual("species",self.match()[1])

    def test_unknown_fixed_foil_rarity_and_special_printing(self):
        for rarity in ["R","RR","AR",None]:
            self.setUp();self.row["rarity"]=rarity;self.assertEqual("rarity",self.match()[1])
        self.setUp();self.detail["title"]="Bidoof Reverse - VSTAR Universe (Fixed) [s12a-121]"
        self.assertEqual("printing",self.match()[1])
        self.setUp();self.row["rarity"]="U";self.detail["title"]="Bidoof - VSTAR Universe (Common) [s12a-121]"
        self.assertEqual("rarity",self.match()[1])

    def test_wrong_condition_language_and_edition(self):
        for key,value in [("option1","Japanese"),("option2","Played"),("option3","Reverse-Holo")]:
            self.setUp();self.detail["variants"][0][key]=value
            self.assertEqual("retailer_variant",self.match()[1])

    def test_duplicate_eligible_variant_or_wrong_option_topology(self):
        self.detail["variants"].append(copy.deepcopy(self.detail["variants"][0]))
        self.assertEqual("retailer_variant",self.match()[1])
        self.setUp();self.detail["options"][0]["position"]=2
        self.assertEqual("retailer_variant",self.match()[1])

    def test_stock_must_agree_in_all_three_documents(self):
        self.feed["variants"][0]["available"]=False;self.assertEqual("stock",self.match()[1])
        self.setUp();self.detail["variants"][0]["available"]=False;self.assertEqual("stock",self.match()[1])
        self.setUp();self.ld["offers"][0]["availability"]="http://schema.org/OutOfStock"
        self.assertEqual("stock",self.match()[1])

    def test_cents_gross_offer_and_currency_agreement(self):
        self.ld["offers"][0]["price"]=.83;self.assertEqual("price",self.match()[1])
        self.setUp();self.detail["variants"][0]["price"]=True;self.assertEqual("price",self.match()[1])
        self.setUp();self.feed["variants"][0]["price"]="NaN";self.assertEqual("price",self.match()[1])
        self.setUp();self.assertEqual("currency",self.match("USD")[1])
        self.ld["offers"][0]["priceCurrency"]="USD";self.assertEqual("currency",self.match()[1])

    def test_variant_specific_offer_identity_and_multiple_offers(self):
        self.ld["offers"][0]["url"]=self.url+"?variant=3";self.assertEqual("offer",self.match()[1])
        self.setUp();self.ld["offers"].append(copy.deepcopy(self.ld["offers"][0]))
        self.assertEqual("offer",self.match()[1])
        self.setUp();self.detail["id"]=3;self.assertEqual("product_identity",self.match()[1])
        self.setUp();self.ld["url"]="https://other.example/products/bidoof"
        self.assertEqual("product_identity",self.match()[1])

    def test_bundles_subscriptions_and_bulk_discounts_rejected(self):
        for key,value in [("requires_selling_plan",True),("selling_plan_allocations",[{}]),("quantity_price_breaks",[{}])]:
            self.setUp();self.detail["variants"][0][key]=value;self.assertEqual("retailer_variant",self.match()[1])
        self.setUp();self.detail["variants"][0]["quantity_rule"]["min"]=2
        self.assertEqual("bundle",self.match()[1])

    def test_weekly_loader_refreshes_owned_prices_without_calendar_gap(self):
        with patch.object(shop.ko.retail, "db", return_value="[]") as db:
            shop.ko.load_targets("WEB_LAKE_KO")
            sql = db.call_args.args[0]
            self.assertIn("p.source='WEB_LAKE_KO' AND (TRUE)", sql)
            self.assertNotIn("INTERVAL '6 days'", sql)
            self.assertIn("c.language_code='ko'", sql)
            self.assertIn("p.resolution_status='NO_PRICE'", sql)

    def test_german_shop_labels_keep_explicit_korean_identity(self):
        self.feed["title"]="Bidiza - VSTAR Universe (Fixed) [s12a-121]"
        self.feed["options"][0]["name"]="Sprache";self.feed["options"][1]["name"]="Zustand"
        self.feed["variants"][0].update(option1="Koreanisch",option3="Regulär")
        self.assertIsNone(self.match()[1])


toreca=load("resolve-torecacamp-ja-prices")

class JapaneseEditionTests(unittest.TestCase):
    def setUp(self):
        self.v=dict(id=toreca.VARIANT_ID,type="normal",legacyVariant="NORMAL",size="standard",stamps=["1st-edition"])
        self.row=dict(card_id="VS1-133",language_code="ja",set_id="VS1",local_id="133",official_count=141,
                      name="ポケモン反転",image_source_url="image",variant_id=toreca.VARIANT_ID,
                      legacy_variant="NORMAL",variant=self.v,all_variants=[self.v],blueprint_id=141135,
                      expansion_id=1984,identity_method="ja-classic-1st",
                      updated_at="2026-10-09T10:00:00Z",resolution_status="NO_PRICE")
        self.b=dict(id=141135,name="Pokémon Reverse",game_id=5,category_id=73,expansion_id=1984,
                    fixed_properties=dict(collector_number="133/141"))
        v=dict(id=2,title="【状態A】",option1="【状態A】",option2=None,option3=None,sku="sku",available=True,price="680")
        self.p=dict(id=8912641130670,title=toreca.MANIFEST["VS1-133"]["title"],handle="rc_test",
                    tags=["#VS_ポケモンカードVS","ポケモンカードシングル"],
                    options=[dict(name="コンディション")],variants=[v])
        self.detail=copy.deepcopy(self.p);self.detail["variants"][0]["price_currency"]="JPY"
        self.ajax=copy.deepcopy(self.p);self.ajax.update(url="/products/rc_test")
        self.ajax["variants"][0].update(quantity_rule=dict(min=1,increment=1))

    def match(self):
        return toreca.match_offer(self.row,self.p,self.detail,self.ajax,self.b)

    def test_curated_first_edition_with_declared_major_unit_jpy(self):
        o,r=self.match();self.assertIsNone(r);self.assertEqual("680",o["amount"])
        self.assertEqual("JPY",o["currency"])

    def test_unlimited_holo_or_ambiguous_printing_cannot_match(self):
        self.v["stamps"]=[];self.v["subtype"]="unlimited";self.assertIsNotNone(self.match()[1])
        self.setUp();self.v["type"]="holo";self.assertIsNotNone(self.match()[1])
        self.setUp();self.row["all_variants"].append(copy.deepcopy(self.v))
        self.assertEqual("ambiguous_printing",self.match()[1])

    def test_provider_alias_number_game_and_expansion_are_required(self):
        for key,value in [("name","Pokémon Switch"),("id",141134),("game_id",1),("expansion_id",1983)]:
            self.setUp();self.b[key]=value;self.assertEqual("provider_identity",self.match()[1])
        self.setUp();self.b["fixed_properties"]["collector_number"]="134/141"
        self.assertEqual("provider_identity",self.match()[1])

    def test_explicit_unlimited_mapping_does_not_accept_first_edition(self):
        m=toreca.MANIFEST["E3-060"]
        self.v.update(id=m["variant_id"],stamps=[],subtype="unlimited")
        self.row.update(card_id="E3-060",set_id="E3",local_id="060",official_count=87,
                        variant_id=m["variant_id"],blueprint_id=m["blueprint"],expansion_id=m["expansion"],
                        identity_method="ja-classic-unlimited",all_variants=[self.v])
        self.b.update(id=m["blueprint"],name=m["english"],expansion_id=m["expansion"],
                      fixed_properties=dict(collector_number="060"))
        for p in (self.p,self.detail,self.ajax):
            p.update(id=m["product"],title=m["title"])
        self.p["tags"]=[m["primary_tag"],"ポケモンカードシングル"]
        self.assertIsNone(self.match()[1])
        self.v.update(stamps=["1st-edition"],subtype=None)
        self.assertEqual("edition_or_printing",self.match()[1])

    def test_zero_padded_provider_number_and_explicit_denominator(self):
        self.b["fixed_properties"]["collector_number"]="0133"
        self.assertIsNone(self.match()[1])
        self.b["fixed_properties"]["collector_number"]="133/140"
        self.assertEqual("provider_identity",self.match()[1])

    def test_shop_title_product_id_edition_and_language_are_exact(self):
        self.p["title"]=self.p["title"].replace("1ED","アンリミ")
        self.assertEqual("retail_identity",self.match()[1])
        self.setUp();self.p["id"]=4;self.assertEqual("retail_identity",self.match()[1])
        self.setUp();self.p["tags"]=[];self.assertEqual("set_language",self.match()[1])

    def test_condition_a_minus_stock_currency_units_and_amount_rejected(self):
        self.detail["variants"][0]["title"]="【状態A-】";self.assertEqual("condition",self.match()[1])
        self.setUp();self.ajax["variants"][0]["available"]=False;self.assertEqual("stock",self.match()[1])
        self.setUp();self.detail["variants"][0]["price_currency"]="USD";self.assertEqual("currency",self.match()[1])
        self.setUp();self.detail["variants"][0]["price"]="68000";self.assertEqual("price",self.match()[1])


def japanese_postgres_tests():
    c=JapaneseEditionTests();c.setUp()
    u=dict(row=c.row,offer=c.match()[0],base_eur="4.40",fx=".00595",fx_date="2026-10-09",observed_at="2026-10-09T12:00:00Z")
    captured=[]
    with patch.object(toreca.retail,"db",side_effect=lambda sql:captured.append(sql) or "0"):
        toreca.apply_updates([u])
    setup="""
    CREATE TEMP TABLE catalog_cards_mirror(card_id text,language_code text,set_id text,local_id text,name text,image_source_url text,variants jsonb);
    CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,legacy_variant text,source text,base_eur numeric,updated_at timestamptz,resolution_status text,failure_detail text,next_attempt_at timestamptz);
    CREATE TEMP TABLE tcg_price_history(card_id text,language_code text,variant_id text,source text,base_eur numeric,captured_at timestamptz);
    INSERT INTO catalog_cards_mirror VALUES('VS1-133','ja','VS1','133','ポケモン反転','image',""" + toreca.retail.quote(json.dumps(c.row["all_variants"])) + """::jsonb);
    INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,updated_at,resolution_status)
    VALUES('VS1-133','ja',""" + toreca.retail.quote(toreca.VARIANT_ID) + """,'NORMAL','2026-10-09T10:00:00Z','NO_PRICE');
    """
    for label,mutation,expected in [
        ("success_repeat","",[1,0]),
        ("newer_price","UPDATE tcg_price_cache SET updated_at='2026-10-09T11:00:00Z',base_eur=99;",[0]),
        ("changed_image","UPDATE catalog_cards_mirror SET image_source_url='changed';",[0]),
        ("changed_variant","UPDATE catalog_cards_mirror SET variants='[]';",[0]),
        ("wrong_language","UPDATE tcg_price_cache SET language_code='zh-tw';",[0])]:
        query="BEGIN; SET LOCAL statement_timeout='15s';"+setup+mutation+captured[0]*len(expected)
        query+="SELECT COUNT(*) FROM tcg_price_history; ROLLBACK;"
        r=subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-X","-qAt","-v","ON_ERROR_STOP=1"],
                         input=query,text=True,capture_output=True,timeout=25)
        assert r.returncode==0,(label,r.stderr)
        results=[int(x) for x in r.stdout.strip().splitlines()]
        assert results==expected+[sum(expected)],(label,results)
    print("5 Japanese PostgreSQL rollback scenarios passed")


if __name__=="__main__":
    if "--postgres" in sys.argv:
        fixtures=load("test-price-round3")
        fixtures.postgres_tests(source="WEB_LAKE_KO")
        fixtures.postgres_tests(source="WEB_MANA_KO")
        japanese_postgres_tests()
    else:
        unittest.main()
