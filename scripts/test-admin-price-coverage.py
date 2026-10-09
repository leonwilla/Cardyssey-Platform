#!/usr/bin/env python3
"""Exercise the repository's actual SQL in rollback-only PostgreSQL fixtures."""
import json
import re
import subprocess
from pathlib import Path

source = Path('platform/api/src/main/kotlin/de/cardyssey/api/AdminPriceCoverageRepository.kt').read_text()
cte = re.search(r'val coverageCte = """(.*?)"""', source, re.S)[1]
fragments = re.findall(r'val sql = coverageCte \+ """(.*?)"""', source, re.S)
overview = re.sub(r'\$\{if \(language != null\).*?else ""\}', '', fragments[0])
cards = fragments[1].replace('$PAGE_SIZE', '100')


def db(sql):
    result = subprocess.run(
        ['docker', 'exec', '-i', 'cardyssey-db', 'psql', '-U', 'cardyssey', '-d', 'cardyssey', '-X', '-qAt', '-v', 'ON_ERROR_STOP=1'],
        input="BEGIN; SET LOCAL statement_timeout='15s';\n" + sql + '\nROLLBACK;',
        text=True, capture_output=True, check=True, timeout=25,
    )
    return result.stdout.strip().splitlines()


setup = """
CREATE TEMP TABLE catalog_cards_mirror(card_id text,language_code text,set_id text,local_id text,name text,variants jsonb);
CREATE TEMP TABLE catalog_sets_mirror(language_code text,set_id text,name text);
CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,resolution_status text,base_eur numeric,failure_detail text,next_attempt_at timestamptz);
INSERT INTO catalog_sets_mirror VALUES ('ja','S1','日本語'),('de','S1','Deutscher Setname');
INSERT INTO catalog_cards_mirror VALUES
 ('ok-old','ja','S1','1','Valid stale price','[{"id":"normal"}]'),
 ('no-price','ja','S1','2','Missing price','[{"id":"normal"},{"id":"reverse"}]'),
 ('deferred','ja','S1','3','Deferred','[{"id":"normal"}]'),
 ('error','ja','S1','4','Error','[{"id":"normal"}]'),
 ('no-variants','ja','S1','5','No variants','[]'),
 ('bad-variants','ja','S1','6','No valid IDs','[{}]'),
 ('zero','ja','S1','7','Zero','[{"id":"normal"}]'),
 ('nan','ja','S1','8','NaN','[{"id":"normal"}]'),
 ('excluded-pocket','ja','A1','9','Pocket','[]'),
 ('excluded-fr','fr','S1','10','French','[]'),
 ('en-missing','en','S1','11','English','[]');
INSERT INTO tcg_price_cache VALUES
 ('ok-old','ja','normal','PRICE_FOUND',10,NULL,NULL),
 ('no-price','ja','normal','NO_PRICE',NULL,'not matched',NULL),
 ('deferred','ja','normal','NO_PUBLIC_PRICE',NULL,'release hold',NOW()+INTERVAL '7 days'),
 ('error','ja','normal','PROVIDER_ERROR',NULL,'timeout',NULL),
 ('zero','ja','normal','PRICE_FOUND',0,NULL,NULL),
 ('nan','ja','normal','PRICE_FOUND','NaN',NULL,NULL);
"""
query = cte + overview
result = db(setup + '\nSELECT jsonb_agg(to_jsonb(q)) FROM (' + query + ') q;')
groups = json.loads(result[0])
assert len(groups) == 2, groups
ja = next(g for g in groups if g['language_code'] == 'ja')
assert ja['set_name'] == 'Deutscher Setname', ja
assert (ja['affected_cards'], ja['missing_prices'], ja['missing_variant_cards']) == (7, 6, 2), ja
assert (ja['deferred_prices'], ja['provider_errors'], ja['missing_cache']) == (1, 1, 1), ja
print('PASS: set/language grouping, invalid prices, deferred/errors/cache gaps, variant gaps, digital/language exclusions')

def page_sql(offset):
    sql = cards.replace('language_code=?', "language_code='ja'").replace('set_id=?', "set_id='S1'").replace('OFFSET ?', 'OFFSET ' + str(offset))
    return 'SELECT jsonb_agg(to_jsonb(q)) FROM (' + cte + sql + ') q;'

pages = db(setup + page_sql(0) + '\n' + page_sql(100))
first, empty = map(json.loads, pages)
assert len(first) == 8 and all(row['total'] == 8 for row in first), first
assert 'ok-old' not in {row['card_id'] for row in first}, first
assert empty == [dict(total=8, **{key: None for key in first[0] if key != 'total'})], empty
assert next(row for row in first if row['card_id'] == 'deferred')['reason'] == 'NO_PUBLIC_PRICE'
print('PASS: exact set detail, one row per missing variant, consistent pagination total including empty page')

live = db('SELECT COUNT(*) FROM (' + query + ') q;')
assert int(live[0]) > 0
print('PASS: production read-only grouped query,', live[0], 'set/language groups')
