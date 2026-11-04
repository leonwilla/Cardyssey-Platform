#!/usr/bin/env python3
"""Read-only, set-scoped catalog pricing monitor. Values never inferred."""
import sys,json,subprocess
source,language,setid=sys.argv[1:4]
assert source in ('tcg','ebay') and language in ('de','en','ja','ko','zh-cn','zh-tw')
assert setid.replace('-','').replace('_','').isalnum() and len(setid)<90
q=lambda s:"'"+s.replace("'","''")+"'"
cache='tcg_price_cache' if source=='tcg' else 'ebay_price_cache'
extra=" AND c.local_id BETWEEN '094' AND '101'" if source=='ebay' and setid=='mep' else ''
filter_source="AND p.source='CARDYSSEY_EBAY'" if source=='ebay' else ''
query=f"""SELECT COALESCE(json_agg(t),'[]') FROM (SELECT c.card_id as \"cardId\",c.set_id as \"setId\",c.local_id as \"number\",c.name,c.variants, p.base_eur as price, p.source,p.updated_at as \"updatedAt\", p.resolution_status as status,COALESCE(p.failure_detail,rv.failure_reason) as failure,rv.search_query as \"searchQuery\",rv.search_status as \"searchStatus\",rv.search_steps as \"searchSteps\", rv.candidates as \"candidates\" {',p.sample_count as sales' if source=='ebay' else ''} FROM catalog_cards_mirror c LEFT JOIN LATERAL (SELECT * FROM {cache} p WHERE p.card_id=c.card_id AND p.language_code=c.language_code {filter_source} ORDER BY (p.base_eur IS NOT NULL) DESC,p.updated_at DESC LIMIT 1) p ON TRUE LEFT JOIN LATERAL (SELECT search_query,search_status,search_steps,candidates,failure_reason FROM price_review_cases rv WHERE rv.card_id=c.card_id AND rv.language_code=c.language_code ORDER BY rv.checked_at DESC LIMIT 1) rv ON TRUE WHERE c.set_id={q(setid)} AND c.language_code={q(language)} {extra} ORDER BY c.local_id,c.card_id) t;""" if source=='tcg' else f"""SELECT COALESCE(json_agg(t),'[]') FROM (
 SELECT c.card_id as "cardId",c.set_id as "setId",c.local_id as "number",c.name,c.variants,
 COALESCE(e.base_eur,tc.base_eur) AS price,
 CASE WHEN e.base_eur IS NOT NULL THEN 'CARDYSSEY_EBAY' ELSE tc.source END AS source,
 COALESCE(e.updated_at,tc.updated_at) AS "updatedAt",e.base_eur AS "ebayPrice",
 tc.base_eur AS "fallbackPrice",tc.source AS "fallbackSource",
 tc.variant_id AS "fallbackVariantId",tc.legacy_variant AS "fallbackVariant",e.sample_count AS sales
 FROM catalog_cards_mirror c
 LEFT JOIN LATERAL (SELECT base_eur,updated_at,sample_count FROM ebay_price_cache e
   WHERE e.card_id=c.card_id AND e.language_code=c.language_code
   AND e.source='CARDYSSEY_EBAY' AND e.base_eur>0 ORDER BY e.updated_at DESC LIMIT 1) e ON TRUE
 LEFT JOIN LATERAL (SELECT base_eur,source,updated_at,variant_id,legacy_variant FROM tcg_price_cache p
   WHERE p.card_id=c.card_id AND p.language_code=c.language_code AND p.base_eur>0
   ORDER BY CASE WHEN p.source LIKE 'CARDMARKET%' THEN 0
                 WHEN p.source LIKE 'POKEMONTCGIO_CARDMARKET%' THEN 1
                 WHEN p.source LIKE 'TCGCSV%' OR p.source LIKE '%TCGPLAYER%' THEN 2
                 ELSE 3 END,
            CASE WHEN p.legacy_variant='NORMAL' THEN 0 WHEN p.legacy_variant='REVERSE' THEN 1 ELSE 2 END,
            p.updated_at DESC LIMIT 1) tc ON TRUE
 WHERE c.set_id={q(setid)} AND c.language_code={q(language)} {extra}
 ORDER BY c.local_id,c.card_id
 ) t;"""
a=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-Atc',query],timeout=15,text=True)
print(a.strip() or '[]')
