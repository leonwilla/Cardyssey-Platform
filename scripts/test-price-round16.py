#!/usr/bin/env python3
"""Exact native print matching without inventing missing rarity or variants."""
import copy,hashlib,importlib.util,json,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
def load(name):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+".py"));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
bulk=load("resolve-japanese-bulk-retail-prices");pinned=bulk.pinned
class PrintIdentityTests(unittest.TestCase):
    def setUp(self):
        url="https://www.pokemon-card.com/card-search/details.php/card/46457"
        self.row=dict(card_id="official_ja_"+hashlib.sha256(url.encode()).hexdigest()[:24],language_code="ja",
                      identity_count=1,set_id="SVM",local_id="003",native_name="ラフレシア",rarity=None,
                      image_source_url="image",official_url=url,source_revision="revision")
        self.raw=dict(url=url,jp_id=46457,name="ラフレシア",set_name="SVM",number="003",set_total="175",img="image",rarity=None)
    def verify(self):return pinned.verified_record(self.row,self.raw,"revision")
    def test_rarityless_modern_deck_is_verified_without_mutating_rarity(self):
        result=self.verify();self.assertEqual("175",result["printed_total"]);self.assertIsNone(result["rarity"])
        self.assertIsNone(self.row["rarity"]);self.assertIsNone(self.raw["rarity"])
    def test_revision_identity_image_number_native_name_language_and_ambiguity(self):
        for key,value in [("source_revision","new"),("image_source_url","other"),("local_id","004"),("native_name","ピカチュウ"),("language_code","ko"),("identity_count",2),("rarity","rare_c")]:
            self.setUp();self.row[key]=value;self.assertIsNone(self.verify(),key)
        self.setUp();self.raw["jp_id"]=1;self.assertIsNone(self.verify())
    def test_unknown_denominator_old_edition_codes_and_unnumbered_cards_held(self):
        for total in ["","0","unknown"]:
            self.setUp();self.raw["set_total"]=total;self.assertIsNone(self.verify())
        self.setUp();self.row["set_id"]=self.raw["set_name"]="BW1";self.assertIsNone(self.verify())
    def test_numbered_promo_alias_is_proved_by_pinned_denominator(self):
        self.row["set_id"]=self.raw["set_name"]="SMP";self.raw["set_total"]="SM-P"
        result=self.verify();self.assertEqual("SM-P",result["printed_code"])
        self.raw["set_total"]="XY-P";self.assertIsNone(self.verify())
class BulkOfferTests(unittest.TestCase):
    def setUp(self):
        self.row=dict(card_id="official_ja_fixture",language_code="ja",identity_count=1,set_id="SVM",
                      local_id="003",printed_code="SVM",printed_total="175",native_name="ラフレシア",rarity=None,
                      official_url="url",official_number="003/175",source_revision="revision")
        v=dict(id=2,title="Default Title",option1="Default Title",option2=None,option3=None,sku="exact",available=True,price="200")
        self.feed=dict(id=1,title="ラフレシア(D){草}〈003/175〉[SVM]",handle="1234",
                       body_html="状態表記の無いカードは状態Aとなります。",tags=["スカーレット&バイオレットシリーズ"],
                       options=[dict(name="Title")],variants=[v])
        self.detail=copy.deepcopy(self.feed);self.detail["variants"][0].update(price_currency="JPY",quantity_rule=dict(min=1,increment=1))
        self.ajax=copy.deepcopy(self.detail);self.ajax.update(url="/products/1234");self.ajax["variants"][0]["price"]=20000
    def offer(self):return bulk.match_offer(self.row,"hareruya",self.feed,self.detail,self.ajax)
    def test_exact_deck_and_trainer_native_name_not_species_substring(self):
        self.assertEqual("200",self.offer()[0]["amount"])
        self.row["native_name"]="大地の器"
        for p in (self.feed,self.detail,self.ajax):p["title"]="大地の器(D){グッズ}〈003/175〉[SVM]"
        self.assertIsNotNone(self.offer()[0])
        self.row["native_name"]="器";self.assertIsNone(self.offer()[0])
    def test_exact_number_total_code_and_full_title(self):
        for key,value in [("local_id","004"),("printed_total","176"),("printed_code","SV4a"),("native_name","ピカチュウ"),("identity_count",2),("language_code","ko")]:
            self.setUp();self.row[key]=value;self.assertIsNone(self.offer()[0],key)
    def test_mirror_special_stamp_graded_sealed_foreign_prints_held(self):
        for title in ["ラフレシア:モンスターボールミラー(D){草}〈003/175〉[SVM]",
                      "ラフレシア(D){草}〈003/175〉[SVM-Mo]","【PSA10】ラフレシア(D){草}〈003/175〉[SVM]",
                      "【未開封】ラフレシア(D){草}〈003/175〉[SVM]"]:
            self.setUp()
            for p in (self.feed,self.detail):p["title"]=title
            self.assertIsNone(self.offer()[0])
        self.setUp();self.feed["tags"]=["韓国語"];self.assertIsNone(self.offer()[0])
    def test_present_official_rarity_must_agree(self):
        self.row["rarity"]="rare_c";self.assertIsNone(self.offer()[0])
        for p in (self.feed,self.detail,self.ajax):p["title"]=p["title"].replace("(D)","(C)")
        self.assertIsNotNone(self.offer()[0])
    def test_stock_condition_currency_prices_and_units(self):
        for key,value in [("available",False),("title","【状態A-】"),("price",200),("sku","wrong")]:
            self.setUp();self.ajax["variants"][0][key]=value;self.assertIsNone(self.offer()[0])
        self.setUp();self.detail["variants"][0]["price_currency"]="USD";self.assertIsNone(self.offer()[0])
        self.setUp();self.detail["variants"][0]["price"]="201";self.assertIsNone(self.offer()[0])
        self.setUp();self.feed["body_html"]="";self.assertIsNone(self.offer()[0])
    def test_bundles_subscriptions_and_product_mismatch(self):
        for key,value in [("requires_selling_plan",True),("selling_plan_allocations",[{}]),("quantity_price_breaks",[{}])]:
            self.setUp();self.ajax["variants"][0][key]=value;self.assertIsNone(self.offer()[0])
        self.setUp();self.detail["variants"][0]["quantity_rule"]["min"]=2;self.assertIsNone(self.offer()[0])
        self.setUp();self.ajax["id"]=9;self.assertIsNone(self.offer()[0])
        self.setUp();self.ajax["url"]="/products/other";self.assertIsNone(self.offer()[0])
    def test_toreca_uses_only_explicit_condition_a(self):
        for p in (self.feed,self.detail,self.ajax):
            p.update(title="ラフレシア SVM 003/175",tags=["ポケモンカードシングル"],options=[dict(name="コンディション")])
            p["variants"][0].update(title="【状態A】",option1="【状態A】")
        offer,reason=bulk.match_offer(self.row,"toreca",self.feed,self.detail,self.ajax)
        self.assertIsNone(reason);self.assertEqual("WEB_TORECACAMP_JP",offer["source"])
        self.ajax["variants"][0]["title"]="【状態A-】"
        self.assertIsNone(bulk.match_offer(self.row,"toreca",self.feed,self.detail,self.ajax)[0])
    def test_numbered_promo_exact_alias_and_denom(self):
        self.row.update(set_id="SMP",printed_code="SM-P",printed_total="SM-P")
        for p in (self.feed,self.detail,self.ajax):p["title"]="ラフレシア(PROMO){草}〈003/SM-P〉[SM-P]"
        self.assertIsNotNone(self.offer()[0])
        self.row["printed_total"]="XY-P";self.assertIsNone(self.offer()[0])
class AjaxCurrencyTests(BulkOfferTests):
    def offer(self):
        return bulk.match_ajax_offer(self.row,"hareruya",self.feed,self.ajax,"JPY")
    def test_explicit_same_session_presentment_currency(self):
        self.assertIsNone(bulk.match_ajax_offer(self.row,"hareruya",self.feed,self.ajax,"EUR")[0])
        self.assertEqual("JPY",self.offer()[0]["currency"])
    def test_live_condition_guide_not_just_old_feed(self):
        self.ajax["body_html"]=None;self.ajax["description"]=""
        self.assertIsNone(self.offer()[0])
    # The inherited triple-document tests intentionally modify Product JSON,
    # which is not an input to this validator; exercise Ajax guards separately.
    def test_stock_condition_currency_prices_and_units(self):
        for key,value in [("available",False),("title","【状態A-】"),("price",200),("sku","wrong")]:
            self.setUp();self.ajax["variants"][0][key]=value;self.assertIsNone(self.offer()[0])
    def test_bundles_subscriptions_and_product_mismatch(self):
        self.ajax["variants"][0]["quantity_rule"]["min"]=2;self.assertIsNone(self.offer()[0])
        self.setUp();self.ajax["id"]=9;self.assertIsNone(self.offer()[0])
class InventoryScopeTests(unittest.TestCase):
    def test_hareruya_xy_collection_only_for_numbered_xy_promos(self):
        for rows,expected in [([],3),([dict(set_id="XYP")],4)]:
            with patch.object(bulk,"get",return_value={"products":[]}) as get:
                result=bulk.fetch_inventory("hareruya",rows)
            self.assertTrue(result["complete"]);self.assertEqual(expected,len(result["scope"]))
            self.assertEqual(expected,get.call_count)
            self.assertEqual("xy" in result["scope"],bool(rows))
    def test_toreca_explicit_promo_handles_and_exact_regular_set_prefix(self):
        registry={"collections":[dict(handle=h) for h in ["xy-promo","sv-promo","sv1s-single","sv1s2-other","champions-path"]]}
        def get(url):return registry if "/collections.json" in url else {"products":[]}
        with patch.object(bulk,"get",side_effect=get):
            result=bulk.fetch_inventory("toreca",[dict(set_id=s) for s in ["XYP","SV-P","SV1S"]])
        self.assertEqual(["sv-promo","sv1s-single","xy-promo"],result["scope"])
stock=load("cardtrader-single-stock")
class MarketplaceStockTests(unittest.TestCase):
    def test_multiple_stock_units_require_explicit_single_card_bundle(self):
        self.assertTrue(stock.is_single_card_stock(dict(quantity=5,bundle_size=1,bundled_quantity=5)))
        self.assertFalse(stock.is_single_card_stock(dict(quantity=5)))
        self.assertTrue(stock.is_single_card_stock(dict(quantity=1)))
    def test_empty_boolean_nonunit_and_inconsistent_bundle_quantities_held(self):
        for product in [dict(quantity=0,bundle_size=1),dict(quantity=True,bundle_size=1),dict(quantity=5,bundle_size=2),dict(quantity=5,bundle_size=True),dict(quantity=5,bundle_size=1,bundled_quantity=10)]:
            self.assertFalse(stock.is_single_card_stock(product))
english=load("review-english-price-leftovers")
class EnglishMissingOnlyTests(unittest.TestCase):
    def test_found_snapshot_cannot_refresh(self):
        with self.assertRaises(ValueError):english.apply_updates([dict(row=dict(old_status="PRICE_FOUND"))],missing_only=True)
def postgres_tests():
    prior=load("test-price-round12")
    fixture=prior.EnglishReviewTests();fixture.setUp();r=fixture.row
    setup="""CREATE TEMP TABLE catalog_cards_mirror(card_id text,language_code text,set_id text,local_id text,name text,image_source_url text,variants jsonb);
    CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,legacy_variant text,source text,base_eur numeric,
      updated_at timestamptz,resolution_status text,failure_detail text,next_attempt_at timestamptz);
    CREATE TEMP TABLE tcg_price_history(card_id text,language_code text,variant_id text,source text,base_eur numeric,captured_at timestamptz);
    INSERT INTO catalog_cards_mirror VALUES('tk-xy-b-12','en','tk-xy-b','12','Bidoof','image',"""+english.retail.quote(json.dumps(r["old_variants"]))+"""::jsonb);
    INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,updated_at,resolution_status)
      VALUES('tk-xy-b-12','en','generated','NORMAL','2026-10-10T10:00:00Z','NO_PRICE');"""
    price=dict(row=r,status="PRICE_FOUND",source="CARDTRADER_MARKETPLACE",base_eur=".9783",detail=english.REVIEW_PREFIX+" fixture price",next_attempt_at="2026-10-17T10:00:00Z")
    cases=[
      ("missing_price_created","",dict(reviewed_variants=1,prices=1,history=1)),
      ("positive_other_variant_preserved","INSERT INTO tcg_price_cache(card_id,language_code,variant_id,base_eur,resolution_status) VALUES('tk-xy-b-12','en','other',5,'NO_PRICE');",dict(reviewed_variants=0,prices=0,history=0)),
      ("positive_target_with_stale_status_preserved","UPDATE tcg_price_cache SET base_eur=5;",dict(reviewed_variants=0,prices=0,history=0)),
    ]
    for label,mutation,expected in cases:
        before="CREATE TEMP TABLE prices_before AS SELECT * FROM tcg_price_cache;CREATE TEMP TABLE cards_before AS SELECT * FROM catalog_cards_mirror;"
        unchanged="SELECT (SELECT count(*) FROM ((SELECT * FROM tcg_price_cache EXCEPT SELECT * FROM prices_before) UNION ALL (SELECT * FROM prices_before EXCEPT SELECT * FROM tcg_price_cache)) q)+(SELECT count(*) FROM ((SELECT * FROM catalog_cards_mirror EXCEPT SELECT * FROM cards_before) UNION ALL (SELECT * FROM cards_before EXCEPT SELECT * FROM catalog_cards_mirror)) q);" if not expected["prices"] else ""
        sql="BEGIN;SET LOCAL statement_timeout='10s';"+setup+mutation+before+english.apply_sql([price],missing_only=True)+unchanged+"ROLLBACK;"
        out=subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-XqAt","-v","ON_ERROR_STOP=1"],input=sql,text=True,capture_output=True,check=True,timeout=20)
        actual=[json.loads(line) for line in out.stdout.splitlines() if line.startswith("{")]
        assert actual==[expected],(label,actual,expected)
        if not expected["prices"]:assert out.stdout.splitlines()[-1]=="0",(label,out.stdout)
        print("postgres",label,"passed")
if __name__=="__main__":
    if "--postgres" in sys.argv:postgres_tests()
    else:unittest.main()
