#!/usr/bin/env python3
"""Stage Base Set Machamp 8/102 version ambiguity for exact sold-comps review.

Does not write tcg_price_cache or label asking prices as sold. Can be rerun.
"""
import json,subprocess
ids=[(273703,1523,13.66),(660220,1523,111.57),(274780,1535,33.66),(557708,4169,34.33)]
data=[{"match_type":"CARDMARKET_VERSION_DIAGNOSTIC","provider":"CARDMARKET","provider_id":i,
       "expansion_id":e,"trend_eur":v,"verified":False,
       "reason":"Version 1/2 and 1999-2000 copyright not uniquely validated; language and edition unverified"}
      for i,e,v in ids]
data.append({"match_type":"EBAY_FALLBACK","status":"NEEDS_EXACT_SOLD_COMPS",
             "query":"Machamp Machomei Base Set 8/102 copyright 1999-2000 holo ungraded",
             "reason":"No confirmed provider identity for this specific print; compare sold, language, edition, condition"})
payload=json.dumps(data)
sql="""UPDATE price_review_cases r SET search_status='EBAY_FALLBACK',
 candidates=COALESCE((SELECT jsonb_agg(v) FROM jsonb_array_elements(COALESCE(r.candidates,'[]'::jsonb)) v
 WHERE v->>'match_type' NOT IN ('CARDMARKET_VERSION_DIAGNOSTIC','EBAY_FALLBACK')),'[]'::jsonb)
 ||'"""+payload.replace("'","''")+"""'::jsonb,
 failure_reason='Copyright 1999-2000 print not uniquely mapped to Cardmarket versions; eBay sold-comps with language/edition/condition validation required.'
 WHERE r.card_id='base1-8'
 AND r.variant_id='zqq5g2u9n0st0gren5bssktmac2ywqaw'
 AND r.language_code IN ('de','en')
 AND EXISTS(SELECT 1 FROM tcg_price_cache p WHERE p.language_code=r.language_code AND p.card_id=r.card_id AND p.variant_id=r.variant_id AND p.resolution_status='NO_PRICE')
 RETURNING r.language_code,r.card_id,r.search_status;"""
cmd=["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","|","-c",sql]
print(subprocess.run(cmd,check=True,text=True,capture_output=True).stdout)
