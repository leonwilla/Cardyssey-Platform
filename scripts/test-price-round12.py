#!/usr/bin/env python3
"""Pinned Korean identities and English source-specific deferral regressions."""
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

def load(name):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+".py"))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ko=load("resolve-cardtrader-ko-nm-prices")
en=load("review-english-price-leftovers")

class PinnedKoreanTests(unittest.TestCase):
    def setUp(self):
        url="https://pokemoncard.co.kr/cards/detail/BS2024019016"
        self.row=dict(card_id="official_ko_"+hashlib.sha256(url.encode()).hexdigest()[:24],
          language_code="ko",identity_count=1,source_url=url,source_revision="rev",native_name="무쇠잎새 ex",
          image_source_url="https://cards.image.pokemonkorea.co.kr/a.png",set_id="SV8a",local_id="016",rarity="RR")
        self.raw=dict(url=url,ko_id="BS2024019016",lang="ko",name="무쇠잎새 ex",img=self.row["image_source_url"],
          set_name="SV8a",number="016",set_total="187",rarity="RR",card_type="기본 포켓몬 ex",hp=220,attacks=[dict(name="attack")])
        self.names=[{"3":"무쇠잎새","6":"Eisenblatt","9":"Iron Leaves"}]
    def match(self):
        return ko.pinned.verified_species(self.row,self.raw,"rev",self.names,ko.ko.normalize)
    def test_independent_bilingual_species_without_imported_german_field(self):
        self.assertEqual("Eisenblatt",self.match()["6"])
    def test_revision_url_id_and_language_must_agree(self):
        for k,v in [("source_revision","other"),("source_url","https://evil.test/cards/detail/BS2024019016"),("card_id","official_ko_wrong"),("language_code","ja"),("identity_count",2)]:
            self.setUp();self.row[k]=v;self.assertIsNone(self.match())
        for k,v in [("url","other"),("ko_id","other"),("lang","ja")]:
            self.setUp();self.raw[k]=v;self.assertIsNone(self.match())
    def test_name_image_set_number_rarity_and_denominator_must_agree(self):
        for k,v in [("name","다른 이름"),("img","other"),("set_name","SV5M"),("number","017"),("rarity","UR"),("set_total","0"),("set_total","?")]:
            self.setUp();self.raw[k]=v;self.assertIsNone(self.match())
    def test_trainer_containing_a_species_name_cannot_match(self):
        self.row["native_name"]="마그마의 용소";self.raw["name"]=self.row["native_name"];self.raw["card_type"]="스타디움"
        self.names=[{"3":"마그마","6":"Magmar","9":"Magmar"}]
        self.assertIsNone(self.match())
    def test_evolution_labels_have_pokemon_gameplay_fields(self):
        for label in ("Pokémon","기본","1진화","2진화","V진화","M진화","BREAK진화"):
            self.raw["card_type"]=label;self.assertIsNotNone(self.match())
        self.raw["attacks"]=[];self.assertIsNone(self.match())
        self.setUp();self.raw["hp"]=True;self.assertIsNone(self.match())
    def test_longest_species_is_unique(self):
        self.names.append({"3":"무쇠","6":"wrong","9":"wrong"});self.assertEqual("Iron Leaves",self.match()["9"])
        self.names.append(copy.deepcopy(self.names[0]));self.assertIsNone(self.match())
    def test_untranslated_or_unknown_species_held(self):
        self.names=[];self.assertIsNone(self.match())

class EnglishReviewTests(unittest.TestCase):
    def setUp(self):
        self.sp=en.SPEC["tk-xy-b-12"]
        self.row=dict(card_id="tk-xy-b-12",language_code="en",set_id="tk-xy-b",local_id="12",name="Bidoof",
          variant_id="generated",legacy_variant="NORMAL",old_image="image",old_updated="2026-10-10T10:00:00Z",
          old_status="NO_PRICE",variant=dict(id="generated",type="normal",size="standard",stamps=[],legacyVariant="NORMAL"))
        self.row["old_variants"]=[self.row["variant"]]
        self.bp=dict(id=132398,game_id=5,category_id=73,expansion_id=1945,name="Bidoof",tcg_player_id=98161,
          version="Non-Holo | Trainer Kit 12/30",fixed_properties=dict(collector_number="12/30",pokemon_rarity="Fixed"))
        self.product=dict(id=1,blueprint_id=132398,name_en="Bidoof",expansion=dict(id=1945),quantity=1,description="",
          graded=False,on_vacation=False,price=dict(cents=90,currency="EUR"),price_cents=90,price_currency="EUR",
          properties_hash=dict(pokemon_language="en",condition="Near Mint",signed=False,altered=False,first_edition=False,
            pokemon_reverse=False,collector_number="12/30",pokemon_rarity="Fixed"))
    def test_exact_reviewed_identity(self):
        self.assertTrue(en.exact_blueprint(self.row,self.bp,self.sp));self.assertEqual(en.Decimal(".9"),en.listing_amount(self.product,self.bp))
    def test_source_number_version_name_and_tcg_identity_must_agree(self):
        for k,v in [("id",1),("expansion_id",1946),("version","Non-Holo | Trainer Kit 13/30"),("tcg_player_id",98162),("name","Pikachu")]:
            self.setUp();self.bp[k]=v;self.assertFalse(en.exact_blueprint(self.row,self.bp,self.sp))
    def test_catalogue_stamps_size_language_and_finish_must_agree(self):
        for k,v in [("stamps",["winner"]),("size","jumbo"),("type","holo"),("foil","cosmos")]:
            self.setUp();self.row["variant"][k]=v;self.assertFalse(en.expected_variant(self.row,self.sp))
        self.setUp();self.row["language_code"]="ko";self.assertFalse(en.expected_variant(self.row,self.sp))
    def test_english_nm_single_required(self):
        for k,v in [("pokemon_language","kr"),("condition","Moderately Played"),("signed",True),("altered",None),("pokemon_reverse",True),("first_edition",True)]:
            self.setUp();self.product["properties_hash"][k]=v;self.assertIsNone(en.listing_amount(self.product,self.bp))
    def test_bundles_stock_description_and_price_disagreement_held(self):
        for k,v in [("quantity",2),("quantity",True),("bundle_size",2),("description","bundle"),("on_vacation",True),("price_cents",91),("price_currency","USD")]:
            self.setUp();self.product[k]=v;self.assertIsNone(en.listing_amount(self.product,self.bp))
    def test_stock_one_without_bundle_field_can_be_checked(self):
        self.assertIsNotNone(en.listing_amount(self.product,self.bp))
        self.product["bundle_size"]=1;self.assertIsNotNone(en.listing_amount(self.product,self.bp))
    def test_deferral_cannot_claim_a_price_or_cross_language(self):
        u=dict(row=self.row,status="NO_PUBLIC_PRICE",source=None,base_eur=None,detail="review",next_attempt_at=None)
        with patch.object(en.retail,"db") as db:
            for changes in [dict(source="OTHER"),dict(base_eur="1"),dict(status="UNKNOWN")]:
                with self.assertRaises(ValueError):en.apply_updates([u|changes])
            with self.assertRaises(ValueError):en.apply_updates([u,u])
            self.row["language_code"]="ko"
            with self.assertRaises(ValueError):en.apply_updates([u])
            db.assert_not_called()

def postgres_tests():
    fixture=EnglishReviewTests();fixture.setUp();r=fixture.row
    setup="""CREATE TEMP TABLE catalog_cards_mirror(card_id text,language_code text,set_id text,local_id text,name text,image_source_url text,variants jsonb);
    CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,legacy_variant text,source text,base_eur numeric,
      updated_at timestamptz,resolution_status text,failure_detail text,next_attempt_at timestamptz);
    CREATE TEMP TABLE tcg_price_history(card_id text,language_code text,variant_id text,source text,base_eur numeric,captured_at timestamptz);
    INSERT INTO catalog_cards_mirror VALUES('tk-xy-b-12','en','tk-xy-b','12','Bidoof','image',"""+en.retail.quote(json.dumps(r["old_variants"]))+"""::jsonb);
    INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,updated_at,resolution_status)
      VALUES('tk-xy-b-12','en','generated','NORMAL','2026-10-10T10:00:00Z','NO_PRICE');"""
    deferral=dict(row=r,status="NO_PUBLIC_PRICE",source=None,base_eur=None,detail=en.REVIEW_PREFIX+" fixture",next_attempt_at="2026-10-17T10:00:00Z")
    price=dict(row=r,status="PRICE_FOUND",source="CARDTRADER_MARKETPLACE",base_eur=".9783",detail=en.REVIEW_PREFIX+" fixture price",next_attempt_at="2026-10-17T10:00:00Z")
    cases=[
      ("defer", "",deferral, [dict(reviewed_variants=1,prices=0,history=0)]),
      ("defer_replay","",deferral,[dict(reviewed_variants=1,prices=0,history=0),dict(reviewed_variants=0,prices=0,history=0)]),
      ("price","",price,[dict(reviewed_variants=1,prices=1,history=1)]),
      ("price_replay","",price,[dict(reviewed_variants=1,prices=1,history=1),dict(reviewed_variants=0,prices=0,history=0)]),
      ("new_price","UPDATE tcg_price_cache SET resolution_status='PRICE_FOUND',base_eur=99;",deferral,[dict(reviewed_variants=0,prices=0,history=0)]),
      ("new_timestamp","UPDATE tcg_price_cache SET updated_at=NOW();",deferral,[dict(reviewed_variants=0,prices=0,history=0)]),
      ("changed_image","UPDATE catalog_cards_mirror SET image_source_url='changed';",deferral,[dict(reviewed_variants=0,prices=0,history=0)]),
      ("changed_variant","UPDATE catalog_cards_mirror SET variants='[]';",deferral,[dict(reviewed_variants=0,prices=0,history=0)]),
      ("changed_name","UPDATE catalog_cards_mirror SET name='Pikachu';",deferral,[dict(reviewed_variants=0,prices=0,history=0)]),
    ]
    for label,mutation,u,expected in cases:
        sql="BEGIN;SET LOCAL statement_timeout='10s';"+setup+mutation+en.apply_sql([u])*len(expected)+"ROLLBACK;"
        out=subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-XqAt","-v","ON_ERROR_STOP=1"],input=sql,text=True,capture_output=True,check=True,timeout=20)
        actual=[json.loads(line) for line in out.stdout.splitlines() if line.startswith("{")]
        assert actual==expected,(label,actual,expected)
        print("postgres",label,"passed")
if __name__=="__main__":
    if "--postgres" in sys.argv:postgres_tests()
    else:unittest.main()
