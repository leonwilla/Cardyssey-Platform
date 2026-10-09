import importlib.util,subprocess,json
from pathlib import Path
s=importlib.util.spec_from_file_location('a',Path(__file__).with_name('audit-price-coverage.py'));a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
sql="""BEGIN;
CREATE TEMP TABLE catalog_cards_mirror AS SELECT * FROM public.catalog_cards_mirror WHERE FALSE;
CREATE TEMP TABLE tcg_price_cache AS SELECT * FROM public.tcg_price_cache WHERE FALSE;
INSERT INTO catalog_cards_mirror(card_id,language_code,set_id,local_id,details_complete,variants) VALUES
('empty','de','test','001',true,'[]'),
('priced','de','test','002',true,'[{"id":"normal"}]'),
('no-price','de','test','003',true,'[{"id":"normal"}]'),
('partial','de','test','004',true,'[{"id":"normal"},{"id":"reverse"}]'),
('missing-cache','de','test','005',true,'[{"id":"normal"}]'),
('wrong-variant','de','test','006',true,'[{"id":"normal"}]'),
('wrong-language','de','test','007',true,'[{"id":"normal"}]'),
('digital','de','A1','008',true,'[]');
INSERT INTO tcg_price_cache(card_id,language_code,variant_id,resolution_status) VALUES
('priced','de','normal','PRICE_FOUND'),
('no-price','de','normal','NO_PRICE'),
('partial','de','normal','PRICE_FOUND'),
('partial','de','reverse','NO_PUBLIC_PRICE'),
('wrong-variant','de','reverse','PRICE_FOUND'),
('wrong-language','en','normal','PRICE_FOUND');
"""
r=subprocess.run(['docker','exec','-i','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-X','-qAt','-v','ON_ERROR_STOP=1'],input=sql+a.SUMMARY_SQL+'ROLLBACK;',text=True,capture_output=True,check=True,timeout=30)
rows=json.loads(r.stdout.strip());de=next(x for x in rows if x['language_code']=='de')
for k,n in {'catalog_entries':7,'entirely_unpriced_entries':5,'partially_priced_entries':1,'missing_variants':1,'catalog_variants':7,'price_found':2,'no_price':1,'deferred':1,'missing_cache':3}.items():assert de[k]==n,(k,de[k],n)
assert next(x for x in rows if x['language_code']=='en')['catalog_entries']==0
print('PASS: coverage rollback fixture covers wholly/partially priced, missing variant/cache, wrong language/variant, deferred and excluded digital entries')
