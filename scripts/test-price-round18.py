#!/usr/bin/env python3
"""Full-card peer separation, exact retailer print metadata and real SQL safeguards."""
import copy,importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image,ImageDraw
def load(name):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+".py"));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load("resolve-japanese-image-print-prices")
prior=load("test-price-round16")
class ImageTests(unittest.TestCase):
    def test_unique_full_card_and_foil_body_match(self):
        image=Image.new("RGB",(217,303),(100,110,120));rival=Image.new("RGB",(217,303),(200,210,220))
        cid,scores=m.select_print(image,{"exact":image,"rival":rival})
        self.assertEqual("exact",cid);self.assertEqual(0,scores[0]["body"])
    def test_recompression_level_match_and_fourfold_separation(self):
        image=Image.new("RGB",(217,303),(100,110,120))
        best=Image.new("RGB",(217,303),(102,112,122))
        for error,expected in [(7,None),(8,"best")]:
            rival=Image.new("RGB",(217,303),(100+error,110+error,120+error))
            self.assertEqual(expected,m.select_print(image,{"best":best,"rival":rival})[0])
        # A rival eight units away is held when the best is 2.5 away: ratio <4.
        with patch.object(m,"distances",side_effect=[dict(whole=2.5,body=2.5),dict(whole=8,body=8)]):
            self.assertIsNone(m.select_print(image,{"best":best,"rival":best})[0])
    def test_close_competitor_and_identical_peer_are_held(self):
        image=Image.new("RGB",(217,303),(100,110,120))
        for rival in [image.copy(),Image.new("RGB",(217,303),(105,115,125))]:
            self.assertIsNone(m.select_print(image,{"one":image,"two":rival})[0])
    def test_artwork_match_with_wrong_foil_body_is_held(self):
        image=Image.new("RGB",(217,303),(100,110,120));wrong=image.copy()
        ImageDraw.Draw(wrong).rectangle(m.BODY,fill=(200,210,220))
        distant=Image.new("RGB",(217,303),(220,220,220))
        self.assertIsNone(m.select_print(image,{"wrong":wrong,"distant":distant})[0])
    def test_distinct_artwork_with_same_foil_body_is_held(self):
        image=Image.new("RGB",(217,303),(100,110,120));rival=Image.new("RGB",(217,303),(200,210,220))
        rival.paste(image.crop(m.BODY),m.BODY)
        self.assertIsNone(m.select_print(image,{"one":image,"two":rival})[0])
    def test_single_peer_and_all_poor_matches_held(self):
        image=Image.new("RGB",(217,303),(100,110,120))
        self.assertIsNone(m.select_print(image,{"one":image})[0])
        self.assertIsNone(m.select_print(image,{"one":Image.new("RGB",(217,303),"white"),"two":Image.new("RGB",(217,303),"black")})[0])
    def test_only_full_card_resolution_and_aspect_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"image.png"
            for size in [(100,140),(600,600),(868,1212)]:
                Image.new("RGB",size).save(path)
                if size==(868,1212):self.assertEqual((217,303),m.prepare_image(path).size)
                else:
                    with self.assertRaises(ValueError):m.prepare_image(path)
class MetadataTests(unittest.TestCase):
    def setUp(self):
        f=prior.BulkOfferTests();f.setUp();self.row=f.row;self.row["identity_count"]=3
        self.feed=f.feed;self.ajax=f.ajax
    def test_nonunique_metadata_requires_separate_image_proof_ordinary_reader_stays_strict(self):
        self.assertTrue(m.metadata_matches(self.row,"hareruya",self.feed))
        self.assertFalse(m.bulk.identity_matches(self.row,"hareruya",self.feed))
    def test_native_language_number_denom_code_and_rarity_must_match(self):
        for key,value in [("language_code","ko"),("native_name","フレシア"),("local_id","004"),("printed_total","176"),("printed_code","SV4a"),("rarity","rare_c")]:
            self.setUp();self.row[key]=value;self.assertFalse(m.metadata_matches(self.row,"hareruya",self.feed))
    def test_explicit_mirror_suffix_must_agree_with_caption(self):
        self.feed["title"]="ラフレシア:モンスターボールミラー(D){草}〈003/175〉[SVM-Mo]"
        self.assertEqual("pokeball",m.parsed_identity("hareruya",self.feed)["printing"])
        self.feed["title"]=self.feed["title"].replace("-Mo]","-Ma]")
        self.assertIsNone(m.parsed_identity("hareruya",self.feed))
    def test_omitted_retail_rarity_requires_image_route_and_wrong_explicit_rarity_held(self):
        self.row["rarity"]="rare_c"
        self.feed.update(title="ラフレシア ミラー SVM 003/175",tags=["ポケモンカードシングル"])
        self.assertTrue(m.metadata_matches(self.row,"toreca",self.feed))
        self.assertFalse(m.bulk.identity_matches(self.row,"toreca",self.feed))
        self.assertEqual("rare_c",self.row["rarity"])
        self.feed["title"]="ラフレシア ミラー U SVM 003/175"
        self.assertFalse(m.metadata_matches(self.row,"toreca",self.feed))
    def test_generic_reverse_does_not_invent_pokeball_foil(self):
        self.feed.update(title="ラフレシア ミラー SVM 003/175",tags=["ポケモンカードシングル"])
        identity=m.parsed_identity("toreca",self.feed)
        self.assertEqual("reverse",identity["printing"]);self.assertNotIn("foil",m.VARIANTS[identity["printing"]])
        self.feed["title"]="マスターボール)"+self.feed["title"]
        self.assertEqual("masterball",m.parsed_identity("toreca",self.feed)["printing"])
    def test_graded_foreign_bundle_and_missing_default_condition_held(self):
        for prefix in ["PSA10 ","韓国 ","海外 ","bundle "]:
            self.setUp();self.feed["title"]=prefix+self.feed["title"];self.assertIsNone(m.parsed_identity("hareruya",self.feed))
        self.setUp();self.feed["body_html"]="";self.assertIsNone(m.parsed_identity("hareruya",self.feed))
    def test_live_price_validation_retains_currency_stock_quantity_and_product_checks(self):
        self.assertIsNotNone(m.bulk.match_ajax_offer(self.row,"hareruya",self.feed,self.ajax,"JPY",identity_validator=m.metadata_matches,identity_parser=m.parsed_identity)[0])
        for field,value in [("available",False),("price",200),("quantity_rule",dict(min=2,increment=1)),("sku","wrong")]:
            self.setUp();self.ajax["variants"][0][field]=value
            self.assertIsNone(m.bulk.match_ajax_offer(self.row,"hareruya",self.feed,self.ajax,"JPY",identity_validator=m.metadata_matches,identity_parser=m.parsed_identity)[0])
        self.setUp();self.assertIsNone(m.bulk.match_ajax_offer(self.row,"hareruya",self.feed,self.ajax,"EUR",identity_validator=m.metadata_matches,identity_parser=m.parsed_identity)[0])
    def test_external_image_hosts_and_missing_images_held(self):
        for url in ["http://cdn.shopify.com/a.jpg","https://evil.example/a.jpg","https://cdn.shopify.com.evil.example/a.jpg"]:
            self.assertIsNone(m.image_url(dict(images=[dict(src=url)])))
        self.assertEqual("https://cdn.shopify.com/a.jpg",m.image_url(dict(images=["//cdn.shopify.com/a.jpg"])))
    def test_metadata_relaxation_preserves_real_multiplicity_and_pin_checks(self):
        fixture=prior.PrintIdentityTests();fixture.setUp();fixture.row["identity_count"]=3
        self.assertIsNone(m.pinned.verified_record(fixture.row,fixture.raw,"revision"))
        self.assertEqual(3,m.pinned.verified_record(fixture.row,fixture.raw,"revision",require_unique=False)["identity_count"])
        fixture.raw["img"]="wrong"
        self.assertIsNone(m.pinned.verified_record(fixture.row,fixture.raw,"revision",require_unique=False))
    def test_writer_rejects_unknown_finish_and_variant_reclassification(self):
        with self.assertRaises(ValueError):m.ja.apply_updates([],variant=dict(m.REVERSE,foil="unknown"))
        with self.assertRaises(ValueError):m.ja.apply_updates([dict(row=dict(old_variants=[m.ja.VARIANT]))],variant=m.REVERSE)
def postgres_tests():
    setup="""CREATE TEMP TABLE catalog_cards_mirror(card_id text,language_code text,set_id text,local_id text,raw_payload jsonb,image_source_url text,variants jsonb);
    CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,legacy_variant text,source text,base_eur numeric,updated_at timestamptz,resolution_status text,failure_detail text,next_attempt_at timestamptz,UNIQUE(card_id,language_code,variant_id));
    CREATE TEMP TABLE tcg_price_history(card_id text,language_code text,variant_id text,source text,base_eur numeric,captured_at timestamptz);"""
    row=dict(card_id="official_ja_fixture",language_code="ja",set_id="SV8a",local_id="143",native_name="大地の器",image_source_url="image",old_variants=[],old_updated=None,old_status=None)
    source="WEB_TORECACAMP_JP";q=m.ja.retail.quote
    count=0
    for variant in m.VARIANTS.values():
        update=dict(row=row,offer=dict(source=source),base_eur="1",observed_at="2026-10-11T12:00:00Z")
        sqls=[]
        with patch.object(m.ja.retail,"db",side_effect=lambda sql:sqls.append(sql) or '{"variants":0,"prices":0,"history":0}'):
            m.ja.apply_updates([update],source,missing_only=True,variant=variant)
        insert="INSERT INTO catalog_cards_mirror VALUES("+",".join(map(q,["official_ja_fixture","ja","SV8a","143",json.dumps(dict(name="大地の器")),"image","[]"]))+");"
        for label,extra,expected in [("missing","",dict(variants=1,prices=1,history=1)),
            ("other_positive","INSERT INTO tcg_price_cache(card_id,language_code,variant_id,base_eur,resolution_status) VALUES('official_ja_fixture','ja','other',5,'NO_PRICE');",dict(variants=0,prices=0,history=0))]:
            verification=("DO $$ BEGIN IF (SELECT variants FROM catalog_cards_mirror)<>"+q(json.dumps([variant]))+"::jsonb OR (SELECT legacy_variant FROM tcg_price_cache)<>"+q(variant["legacyVariant"])+" THEN RAISE EXCEPTION 'wrong variant'; END IF; END $$;") if label=="missing" else ""
            sql="BEGIN;"+setup+insert+extra+sqls[0]+verification+sqls[0]+"ROLLBACK;"
            result=subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-XqAt","-v","ON_ERROR_STOP=1"],input=sql,text=True,capture_output=True,check=True,timeout=25)
            actual=[json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
            assert actual==[expected,dict(variants=0,prices=0,history=0)],(label,actual)
            count+=1
        refresh_row=dict(row,old_variants=[variant],old_updated="2026-10-10T12:00:00Z",old_status="PRICE_FOUND")
        update=dict(update,row=refresh_row);sqls=[]
        with patch.object(m.ja.retail,"db",side_effect=lambda sql:sqls.append(sql) or '{"variants":0,"prices":0,"history":0}'):
            m.ja.apply_updates([update],source,variant=variant)
        seeded=insert+"UPDATE catalog_cards_mirror SET variants="+q(json.dumps([variant]))+"::jsonb; INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,source,base_eur,updated_at,resolution_status) VALUES('official_ja_fixture','ja','generated',"+q(variant['legacyVariant'])+","+q(source)+",5,'2026-10-10T12:00:00Z','PRICE_FOUND');"
        check="DO $$ BEGIN IF (SELECT base_eur FROM tcg_price_cache)<>1 OR (SELECT variants FROM catalog_cards_mirror)<>"+q(json.dumps([variant]))+"::jsonb THEN RAISE EXCEPTION 'weekly refresh failed'; END IF; END $$;"
        result=subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-XqAt","-v","ON_ERROR_STOP=1"],input="BEGIN;"+setup+seeded+sqls[0]+check+sqls[0]+"ROLLBACK;",text=True,capture_output=True,check=True,timeout=25)
        actual=[json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
        assert actual==[dict(variants=0,prices=1,history=1),dict(variants=0,prices=0,history=0)],actual
        count+=1
    print("PASS",count,"PostgreSQL actual variant, other-positive preservation and replay cases")
if __name__=="__main__":
    if "--postgres" in sys.argv:postgres_tests()
    else:unittest.main()

