#!/usr/bin/env python3
"""Idempotent all-set policy for the six supported Cardyssey languages.

Classify exact catalog print IDs; prefer regional exact-language market sources
and keep missing/locality-uncertain values explicit. Never edits price caches.
Run daily or after catalog import. Output is suitable for admin coverage reports.
"""
import argparse,json,subprocess
from pathlib import Path

LANGUAGES=('de','en','ja','ko','zh-cn','zh-tw')
BULK_RARITIES=('häufig', 'ungewöhnlich', 'common', 'uncommon', 'c', 'u', 'rare_c', 'rare_u', 'rare_c_c', 'rare_u_c', 'one diamond', 'two diamond', 'une diamant', 'deux diamant')

SQL="""
WITH catalog AS (
 SELECT c.language_code,c.card_id,c.set_id,c.rarity,
        coalesce(nullif(v.value->>'id',''),'__NO_EXACT_PRINT__') AS variant_id,
        lower(trim(coalesce(c.rarity,''))) AS rarity_key,
        v.value->>'legacyVariant' AS legacy_variant
 FROM catalog_cards_mirror c
 LEFT JOIN LATERAL jsonb_array_elements(c.variants) v(value) ON TRUE
 WHERE c.language_code IN ('de','en','ja','ko','zh-cn','zh-tw')
), classified AS (
 SELECT *, CASE
  WHEN rarity_key IN ('häufig','ungewöhnlich','common','uncommon','c','u','rare_c','rare_u','rare_c_c','rare_u_c','one diamond','two diamond','une diamant','deux diamant') THEN 'BULK'
  WHEN rarity_key IN ('','none','keine','unknown','n/a','unbekannt') THEN 'RARITY_UNVERIFIED'
  ELSE 'SPECIAL' END AS price_class
 FROM catalog
), candidates AS (
 SELECT c.*,
   p.source,p.base_eur,p.updated_at,
   row_number() OVER (PARTITION BY c.language_code,c.card_id,c.variant_id
      ORDER BY
        CASE
        WHEN c.language_code IN ('de','en') AND p.source LIKE 'CARDMARKET%' THEN 0
        WHEN c.language_code='en' AND p.source='POKEMONTCGIO_CARDMARKET' THEN 1
        WHEN c.language_code IN ('de','en') AND p.source IN ('TCGDEX','TCGDEX_CATALOG','TCGDEX_CATALOG_CACHE') THEN 2
        WHEN c.language_code='en' AND p.source LIKE 'TCGCSV_TCGPLAYER%' THEN 3
        WHEN c.language_code='en' AND p.source='POKEMONTCGIO_TCGPLAYER' THEN 4
        WHEN c.language_code='ja' AND (p.source LIKE 'WEB_%_JP' OR p.source LIKE 'CARDTRADER_JP%') THEN 0
        WHEN c.language_code='ja' AND p.source='TCGCSV_JP_MARKET' THEN 1
        WHEN c.language_code='ja' AND p.source LIKE 'TCGDEX%' AND p.source NOT LIKE '%TCGPLAYER%' THEN 2
        WHEN c.language_code='ja' AND p.source LIKE 'CARDTRADER%' THEN 3
        WHEN c.language_code='ko' AND (p.source LIKE 'WEB_%_KO' OR p.source LIKE 'CARDTRADER_KO%') THEN 0
        WHEN c.language_code='ko' AND p.source LIKE 'TCGDEX%' AND p.source NOT LIKE '%TCGPLAYER%' THEN 2
        WHEN c.language_code='zh-tw' AND (p.source LIKE 'WEB_%_HK' OR p.source LIKE 'CARDTRADER%') THEN 0
        WHEN c.language_code='zh-tw' AND p.source LIKE 'TCGDEX%' AND p.source NOT LIKE '%TCGPLAYER%' THEN 2
        WHEN c.language_code='zh-cn' AND p.source LIKE 'CARDTRADER%' THEN 0
        ELSE 99 END,
        p.updated_at DESC NULLS LAST
   ) AS source_rank
 FROM classified c
 LEFT JOIN tcg_price_cache p ON c.variant_id<>'__NO_EXACT_PRINT__' AND p.card_id=c.card_id
  AND p.language_code=c.language_code AND p.variant_id=c.variant_id
  AND p.resolution_status='PRICE_FOUND' AND p.base_eur>0
  AND p.source IS NOT NULL AND p.source NOT ILIKE '%PRICECHARTING%'
  AND (
      (c.language_code IN ('de','en') AND (p.source LIKE 'CARDMARKET%' OR (p.source LIKE 'TCGDEX%' AND p.source NOT LIKE '%TCGPLAYER%') OR
         (c.language_code='en' AND (p.source LIKE 'TCGCSV_TCGPLAYER%' OR p.source LIKE 'POKEMONTCGIO_%'))))
   OR (c.language_code='ja' AND (p.source LIKE 'WEB_%_JP' OR p.source LIKE 'CARDTRADER%' OR p.source='TCGCSV_JP_MARKET'))
   OR (c.language_code='ko' AND (p.source LIKE 'WEB_%_KO' OR p.source LIKE 'CARDTRADER_KO%'))
   OR (c.language_code='zh-tw' AND (p.source LIKE 'WEB_%_HK' OR p.source LIKE 'CARDTRADER%'))
   OR (c.language_code='zh-cn' AND p.source LIKE 'CARDTRADER%')
  )
), chosen AS (
 SELECT * FROM candidates WHERE source_rank=1
)
INSERT INTO global_price_source_policy(language_code,card_id,variant_id,set_id,rarity,
 price_class,preferred_market,preferred_provider_family,selected_price_source,
 selected_price_eur,price_status,price_checked_at,policy_updated_at)
SELECT c.language_code,c.card_id,c.variant_id,c.set_id,c.rarity,c.price_class,
 CASE WHEN c.price_class='BULK' THEN 'TCG'
      WHEN c.price_class='SPECIAL' AND c.language_code IN ('de','en') THEN 'EBAY'
      ELSE 'LOCAL_MARKET' END,
 CASE WHEN c.language_code='de' THEN 'CARDMARKET_TCGDEX_DE'
      WHEN c.language_code='en' THEN 'CARDMARKET_TCGDEX_TCGPLAYER_EN'
      WHEN c.language_code='ja' THEN 'JAPAN_DOMESTIC_CARDTRADER_JP'
      WHEN c.language_code='ko' THEN 'KOREA_DOMESTIC_CARDTRADER_KO'
      WHEN c.language_code='zh-tw' THEN 'TAIWAN_HONG_KONG_CARDTRADER_TW'
      WHEN c.language_code='zh-cn' THEN 'CHINA_CARDTRADER_CN'
 END,
 c.source,c.base_eur,
 CASE WHEN c.variant_id='__NO_EXACT_PRINT__' THEN 'NO_EXACT_VARIANT'
      WHEN c.price_class='RARITY_UNVERIFIED' THEN 'RARITY_REVIEW'
      WHEN c.source IS NOT NULL THEN 'PRICE_FOUND'
      ELSE 'MISSING_LOCAL_PRICE' END,
 c.updated_at,now()
FROM chosen c
ON CONFLICT(language_code,card_id,variant_id) DO UPDATE SET
 set_id=EXCLUDED.set_id,rarity=EXCLUDED.rarity,price_class=EXCLUDED.price_class,
 preferred_market=EXCLUDED.preferred_market,
 preferred_provider_family=EXCLUDED.preferred_provider_family,
 selected_price_source=EXCLUDED.selected_price_source,
 selected_price_eur=EXCLUDED.selected_price_eur,
 price_status=EXCLUDED.price_status,price_checked_at=EXCLUDED.price_checked_at,
 policy_updated_at=now()
 WHERE (global_price_source_policy.set_id,global_price_source_policy.rarity,
        global_price_source_policy.price_class,global_price_source_policy.preferred_market,
        global_price_source_policy.preferred_provider_family,
        global_price_source_policy.selected_price_source,global_price_source_policy.selected_price_eur,
        global_price_source_policy.price_status,global_price_source_policy.price_checked_at)
 IS DISTINCT FROM
       (EXCLUDED.set_id,EXCLUDED.rarity,EXCLUDED.price_class,EXCLUDED.preferred_market,
        EXCLUDED.preferred_provider_family,EXCLUDED.selected_price_source,EXCLUDED.selected_price_eur,
        EXCLUDED.price_status,EXCLUDED.price_checked_at);
"""
REPORT="""SELECT jsonb_build_object(
 'languages',jsonb_object_agg(language_code,stats),
 'totalPrints',(SELECT count(*) FROM global_price_source_policy),
 'totalBulkPrints',(SELECT count(*) FROM global_price_source_policy WHERE price_class='BULK'),
 'missingPrints',(SELECT count(*) FROM global_price_source_policy WHERE selected_price_eur IS NULL),
 'sets',(SELECT count(DISTINCT (language_code,set_id)) FROM global_price_source_policy),
 'generatedAt',now()
)::text FROM (
 SELECT language_code,jsonb_build_object(
  'prints',count(*),'cards',count(DISTINCT card_id),'sets',count(DISTINCT set_id),
  'bulkPrints',count(*) FILTER(WHERE price_class='BULK'),
  'bulkWithPrice',count(*) FILTER(WHERE price_class='BULK' AND selected_price_eur IS NOT NULL),
  'missing',count(*) FILTER(WHERE selected_price_eur IS NULL),
  'noExactVariant',count(*) FILTER(WHERE variant_id='__NO_EXACT_PRINT__'),
  'rarityUnknown',count(*) FILTER(WHERE price_class='RARITY_UNVERIFIED'),
  'sources',jsonb_object_agg(COALESCE(selected_price_source,'NO_PRICE'),num)
 ) stats FROM (SELECT language_code,card_id,set_id,variant_id,price_class,selected_price_eur,
    selected_price_source,count(*) OVER (PARTITION BY language_code,COALESCE(selected_price_source,'NO_PRICE')) num
  FROM global_price_source_policy) x GROUP BY language_code
) s;"""

def execute(sql):
    proc=subprocess.run(['docker','exec','-i','cardyssey-db','psql','-X','-v','ON_ERROR_STOP=1',
                         '-U','cardyssey','-d','cardyssey','-At'],input=sql,text=True,
                         capture_output=True,timeout=200,check=True)
    return proc.stdout.strip()

def sync(report_path):
    execute(SQL)
    # Keep the monitor accurate if catalog entries/prints are removed.
    execute("""DELETE FROM global_price_source_policy p WHERE NOT EXISTS (
       SELECT 1 FROM catalog_cards_mirror c
       WHERE c.card_id=p.card_id AND c.language_code=p.language_code
         AND (p.variant_id='__NO_EXACT_PRINT__' AND jsonb_array_length(c.variants)=0
              OR EXISTS (SELECT 1 FROM jsonb_array_elements(c.variants) v WHERE v->>'id'=p.variant_id)));""")
    summary=json.loads(execute(REPORT))
    execute("INSERT INTO global_price_policy_sync(id,total_prints,bulk_prints,missing_prints,summary) VALUES(1,"+
       str(summary['totalPrints'])+","+str(summary['totalBulkPrints'])+","+str(summary['missingPrints'])+","+
       "'"+json.dumps(summary).replace("'","''")+"'::jsonb) ON CONFLICT(id) DO UPDATE SET total_prints=EXCLUDED.total_prints,bulk_prints=EXCLUDED.bulk_prints,missing_prints=EXCLUDED.missing_prints,summary=EXCLUDED.summary,last_success_at=now();")
    Path(report_path).parent.mkdir(parents=True,exist_ok=True)
    Path(report_path).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',default='/home/tv/.cache/cardyssey/global-price-source-coverage.json')
    args=parser.parse_args()
    result=sync(args.report)
    print(json.dumps({k:result[k] for k in ('totalPrints','totalBulkPrints','missingPrints','sets')},ensure_ascii=False))
