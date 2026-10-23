#!/usr/bin/env python3
"""Read-only, set-scoped catalog pricing monitor. Values never inferred."""
import sys,json,subprocess
source,language,setid=sys.argv[1:4]
assert source in ('tcg','ebay') and language in ('de','en','ja','ko','zh-cn','zh-tw')
assert setid.replace('-','').replace('_','').isalnum() and len(setid)<90
q=lambda s:"'"+s.replace("'","''")+"'"
cache='tcg_price_cache' if source=='tcg' else 'ebay_price_cache'
filter_source="AND p.source='CARDYSSEY_EBAY'" if source=='ebay' else ''
query=f"""SELECT COALESCE(json_agg(t),'[]') FROM (SELECT c.card_id as \"cardId\",c.set_id as \"setId\",c.local_id as \"number\",c.name,c.variants, p.base_eur as price, p.source,p.updated_at as \"updatedAt\", p.resolution_status as status,COALESCE(p.failure_detail,rv.failure_reason) as failure,rv.search_query as \"searchQuery\",rv.search_status as \"searchStatus\",rv.search_steps as \"searchSteps\", rv.candidates as \"candidates\" {',p.sample_count as sales' if source=='ebay' else ''} FROM catalog_cards_mirror c LEFT JOIN LATERAL (SELECT * FROM {cache} p WHERE p.card_id=c.card_id AND p.language_code=c.language_code {filter_source} ORDER BY (p.base_eur IS NOT NULL) DESC,p.updated_at DESC LIMIT 1) p ON TRUE LEFT JOIN LATERAL (SELECT search_query,search_status,search_steps,candidates,failure_reason FROM price_review_cases rv WHERE rv.card_id=c.card_id AND rv.language_code=c.language_code ORDER BY rv.checked_at DESC LIMIT 1) rv ON TRUE WHERE c.set_id={q(setid)} AND c.language_code={q(language)} ORDER BY c.local_id,c.card_id) t;""" if source=='tcg' else f"""SELECT COALESCE(json_agg(t),'[]') FROM (SELECT c.card_id as \"cardId\",c.set_id as \"setId\",c.local_id as \"number\",c.name,c.variants, p.base_eur as price, p.source,p.updated_at as \"updatedAt\", p.sample_count as sales FROM catalog_cards_mirror c LEFT JOIN LATERAL (SELECT * FROM ebay_price_cache p WHERE p.card_id=c.card_id AND p.language_code=c.language_code AND p.source='CARDYSSEY_EBAY' ORDER BY p.updated_at DESC LIMIT 1) p ON TRUE WHERE c.set_id={q(setid)} AND c.language_code={q(language)} ORDER BY c.local_id,c.card_id) t;"""
a=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-Atc',query],timeout=15,text=True)
print(a.strip() or '[]')
