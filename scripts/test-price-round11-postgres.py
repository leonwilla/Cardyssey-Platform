import importlib.util,json,subprocess,copy
from pathlib import Path
from unittest.mock import patch
def load(name):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+".py"));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ko=load("resolve-cardtrader-ja-nm-prices");ja=load("resolve-hareruya-ja-prices")
class MatchTests:
 def setUp(self):
  self.row=dict(card_id="official_ja_test",language_code="ja",set_id="SV9",local_id="101",native_name="マラカッチ",image_source_url="https://official/image",old_variants=[],old_updated=None,old_status=None)
 def match(self):return dict(source=ko.SOURCE,currency="EUR",amount="1.4"),None
def postgres_tests(source=ko.SOURCE):
    def db(sql):
        r=subprocess.run(['docker','exec','-i','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-X','-qAt','-v','ON_ERROR_STOP=1'],
            input="BEGIN; SET LOCAL statement_timeout='15s';\n"+sql+'\nROLLBACK;',text=True,capture_output=True,check=False,timeout=25)
        if r.returncode:raise RuntimeError(r.stderr)
        return r.stdout.strip().splitlines()
    setup="""
    CREATE TEMP TABLE catalog_cards_mirror (LIKE public.catalog_cards_mirror INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);
    CREATE TEMP TABLE catalog_sets_mirror (LIKE public.catalog_sets_mirror INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);
    CREATE TEMP TABLE catalog_supplemental_cards (LIKE public.catalog_supplemental_cards INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);
    CREATE TEMP TABLE catalog_set_code_aliases (LIKE public.catalog_set_code_aliases INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);
    CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,legacy_variant text,source text,base_eur numeric,updated_at timestamptz,resolution_status text,failure_detail text,next_attempt_at timestamptz,UNIQUE(card_id,language_code,variant_id));
    CREATE TEMP TABLE tcg_price_history(card_id text,language_code text,variant_id text,source text,base_eur numeric,captured_at timestamptz);
    """
    case=MatchTests();case.setUp();update=dict(row=case.row,offer=case.match()[0],base_eur='1.5217',observed_at='2026-10-09T12:00:00Z')
    update['offer']['source']=source
    captured=[]
    with patch.object(ko.retail,'db',lambda sql:captured.append(sql) or '{"variants":0,"prices":0,"history":0}'):
        ko.apply_updates([update],source=source)
    writer=captured[0]
    insert="""INSERT INTO catalog_cards_mirror(language_code,card_id,set_id,local_id,name,image_source_url,variants,raw_payload,details_complete)
        VALUES('ja','official_ja_test','SV9','101','マラカッチ','https://official/image','[]','{"name":"マラカッチ"}',TRUE);
    """
    result=db(setup+insert+writer+writer)
    assert json.loads(result[0])==dict(variants=1,prices=1,history=1),result
    assert json.loads(result[1])==dict(variants=0,prices=0,history=0),result
    concurrent="INSERT INTO tcg_price_cache VALUES('official_ja_test','ja','generated','NORMAL','OTHER',5,NOW(),'PRICE_FOUND',NULL,NULL);"
    result=db(setup+insert+concurrent+writer)
    assert json.loads(result[0])==dict(variants=0,prices=0,history=0),result
    print('PASS: atomic JP catalogue/cache/history import, repeat-run idempotence, concurrent newer prices preserved')

    details=dict(id='official_ja_test',languageCode='ja',setId='SV9',localId='101',name='マラカッチ',
        imageBase='https://official/image',setName='Test',officialCount=100,rarity='AR',variants=[])
    payload=dict(sourceId='official_ja_test',details=details,allowMatch=False,sourceUrl='https://official/source',revision='test',germanSpecies='Maracamba')
    imported=Path('scripts/catalog-supplemental-import.sql').read_text()
    def rows(p):return "CREATE TEMP TABLE source_rows(payload jsonb) ON COMMIT DROP; INSERT INTO source_rows VALUES("+ko.retail.quote(json.dumps(p))+"::jsonb);"
    # Run the actual supplement importer twice, using separate temporary staging tables.
    drop='DROP TABLE source_rows,resolved_rows,invalidated_price_prints;'
    check="SELECT jsonb_build_object('variants',jsonb_array_length(variants),'proof',raw_payload->>'_cardyssey_retail_variant_source') FROM catalog_cards_mirror;"
    first=rows(payload)+imported+writer+drop
    changed=copy.deepcopy(payload);changed['details']['imageBase']='https://official/corrected-image'
    result=db(setup+first+rows(payload)+imported+check+drop+rows(changed)+imported+check+
              "SELECT resolution_status || ':' || COALESCE(base_eur::text,'NULL') FROM tcg_price_cache;")
    assert json.loads(result[1])==dict(variants=1,proof=source),result
    assert json.loads(result[2])==dict(variants=0,proof=None),result
    assert result[3]=='NO_PRICE:NULL',result
    print('PASS: unchanged official imports preserve provenance; changed images clear derived variants/prices')

    # The generalized retail writer must match both card ID AND language.
    captured=[];ja_update=dict(row=dict(card_id='same',language_code='ja',variant_id='normal',updated_at='2026-10-08T00:00:00Z',resolution_status='NO_PRICE'),
        offer=dict(source='WEB_HARERUYA_JP',currency='JPY',amount='500',title="Offer's title",url='https://www.hareruya2.com/products/test',product_id=1),
        base_eur='3',fx='0.006',fx_date='2026-10-09',observed_at='2026-10-09T12:00:00Z')
    with patch.object(ja.retail,'db',lambda sql:captured.append(sql) or '0'):ja.retail.apply_updates([ja_update])
    result=db(setup+"INSERT INTO tcg_price_cache VALUES('same','ja','normal','NORMAL','OLD',NULL,'2026-10-08','NO_PRICE',NULL,NULL),('same','zh-tw','normal','NORMAL','OLD',NULL,'2026-10-08','NO_PRICE',NULL,NULL);"+captured[0]+"SELECT language_code || ':' || resolution_status FROM tcg_price_cache ORDER BY language_code;")
    assert result==['1','ja:PRICE_FOUND','zh-tw:NO_PRICE'],result
    print('PASS: JPY update retains provenance and cannot update a same-ID Chinese price')

    twins=load('repair-verified-catalog-twins')
    variant=json.dumps([dict(id='normal',type='normal',legacyVariant='NORMAL')])
    twin_rows="INSERT INTO catalog_cards_mirror(language_code,card_id,set_id,local_id,name,image_source_url,variants,raw_payload,details_complete) VALUES "
    for card,image in [('canonical','https://same/image'),('derived','https://same/image'),('wrong-image','https://different/image')]:
        twin_rows+="('ja',"+ko.retail.quote(card)+",'TEST','001','Name',"+ko.retail.quote(image)+","+ko.retail.quote(variant)+",'{\"name\":\"Name\"}',TRUE),"
    twin_rows=twin_rows.rstrip(',')+';'
    proof="INSERT INTO tcg_price_cache VALUES('derived','ja','normal','NORMAL','OLD',1,NOW(),'PRICE_FOUND','Exact catalogue duplicate of canonical; exact proof',NULL),('wrong-image','ja','normal','NORMAL','OLD',1,NOW(),'PRICE_FOUND','Exact catalogue duplicate of canonical; exact proof',NULL);"
    result=db(setup+twin_rows+proof+twins.APPLY_SQL+twins.APPLY_SQL+"SELECT card_id FROM catalog_cards_mirror WHERE raw_payload->>'_cardyssey_verified_variant_source'='canonical';")
    assert json.loads(result[0])['catalog_entries_repaired']==1,result
    assert json.loads(result[1])['catalog_entries_repaired']==0,result
    assert result[2:]==['derived'],result
    print('PASS: lost twin provenance restored only with exact identity and saved source evidence; no reciprocal alias or changed-image recovery')

if __name__=="__main__":postgres_tests()
