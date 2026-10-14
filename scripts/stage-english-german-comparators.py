#!/usr/bin/env python3
"""Show existing English card-level reference for matching German variant identity.

Only stage an informational comparator; do not alter price cache or valuation.
The original English language and quote timestamp are retained.
"""
import argparse,subprocess

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--apply",action="store_true")
 a=p.parse_args()
 select="""SELECT COUNT(*) FROM price_reference_candidates e
 JOIN tcg_price_cache d ON d.card_id=e.card_id AND d.variant_id=e.variant_id
 WHERE e.language_code='en' AND d.language_code='de'
   AND d.resolution_status IN ('NO_PRICE','NO_PUBLIC_PRICE')
   AND e.price_eur>0"""
 cmd=["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At"]
 count=subprocess.check_output(cmd+["-c",select],text=True).strip()
 print("eligible_german_comparators",count,"apply",a.apply,flush=True)
 if not a.apply:return
 sql="""INSERT INTO price_reference_candidates
 (language_code,card_id,variant_id,provider,price_eur,currency,evidence,verification_status,observed_at)
 SELECT 'de',e.card_id,e.variant_id,'POKEMONTCGAPI_REFERENCE',
  e.price_eur,e.currency,
  jsonb_build_object('origin_language','en',
   'origin_card_id',e.card_id,'origin_variant_id',e.variant_id,
   'origin_source','POKEMONTCGAPI_REFERENCE',
   'origin_observed_at',e.observed_at,
   'warning','English comparator ONLY, never a German-language price; condition and printing unverified',
   'quotes',e.evidence->'quotes',
   'index',e.evidence->'index'),
   'CROSS_LANGUAGE_REFERENCE',e.observed_at
 FROM price_reference_candidates e
 JOIN tcg_price_cache d ON d.card_id=e.card_id AND d.variant_id=e.variant_id
 WHERE e.language_code='en' AND d.language_code='de'
 AND d.resolution_status IN ('NO_PRICE','NO_PUBLIC_PRICE')
 AND e.price_eur>0
 ON CONFLICT(language_code,card_id,variant_id,provider)
 DO UPDATE SET price_eur=EXCLUDED.price_eur,
 evidence=EXCLUDED.evidence,observed_at=EXCLUDED.observed_at,
 verification_status='CROSS_LANGUAGE_REFERENCE';"""
 out=subprocess.check_output(cmd+["-c",sql],text=True)
 print(out.strip())
if __name__=="__main__":main()
