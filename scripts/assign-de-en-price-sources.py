#!/usr/bin/env python3
"""Idempotent DE/EN exact provider assignment, without inventing product crosswalks.
Run --apply to populate only confirmed provider-specific rows; no price changes.
"""
import argparse,json,subprocess
p=argparse.ArgumentParser()
p.add_argument("--apply",action="store_true")
p.add_argument("--report",default="/tmp/cardyssey-de-en-source-routing.json")
args=p.parse_args()
base=["docker","exec","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey","-At","-c"]
def sql(query):
 return subprocess.run(base+[query],check=True,capture_output=True,text=True).stdout.strip()
setup="""
CREATE TABLE IF NOT EXISTS price_source_routing (
 language_code text NOT NULL,
 card_id text NOT NULL,
 variant_id text NOT NULL,
 primary_provider text NOT NULL,
 provider_product_id text,
 provider_product_url text,
 source_evidence text NOT NULL,
 verification_state text NOT NULL DEFAULT 'SOURCE_ONLY',
 fallback_provider text,
 refresh_days integer NOT NULL DEFAULT 14 CHECK(refresh_days BETWEEN 1 AND 365),
 last_attempt_at timestamptz,
 last_success_at timestamptz,
 next_attempt_at timestamptz,
 failure_count integer NOT NULL DEFAULT 0,
 paused_until timestamptz,
 updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(language_code,card_id,variant_id),
 CHECK(language_code IN ('de','en'))
);
CREATE INDEX IF NOT EXISTS price_source_routing_next ON price_source_routing(next_attempt_at)
 WHERE verification_state='VERIFIED_PRODUCT_ID';
"""
# Only exact original source. Do not assign generic TCGDEX provider as scraper,
# or derive DE pricing from English TCGplayer product identity.
insert="""
INSERT INTO price_source_routing(
 language_code,card_id,variant_id,primary_provider,provider_product_id,
 source_evidence,verification_state,last_success_at,next_attempt_at)
SELECT p.language_code,p.card_id,p.variant_id,
 CASE WHEN p.source LIKE 'TCGCSV_TCGPLAYER%' THEN 'TCGCSV_TCGPLAYER'
      WHEN p.source IN ('CARDMARKET_OFFICIAL','CARDMARKET_OFFICIAL_CT_IDENTITY',
          'CARDMARKET_WEB','CARDMARKET_DE_NM_WEB') THEN 'CARDMARKET'
      WHEN p.source='CARDTRADER_MARKETPLACE' THEN 'CARDTRADER'
 END,
 CASE WHEN p.source LIKE 'TCGCSV_TCGPLAYER%'
      THEN substring(p.failure_detail from 'TCGplayer product ([0-9]+)')
      ELSE NULL END,
 p.source || '; ' || COALESCE(left(p.failure_detail,500),''),
 CASE WHEN p.source LIKE 'TCGCSV_TCGPLAYER%' THEN 'VERIFIED_PRODUCT_ID' ELSE 'SOURCE_ONLY' END,
 p.updated_at,p.updated_at + INTERVAL '14 days'
FROM tcg_price_cache p
WHERE p.language_code IN ('de','en') AND p.resolution_status='PRICE_FOUND'
 AND p.base_eur>0
 AND (p.source LIKE 'TCGCSV_TCGPLAYER%' OR p.source IN
 ('CARDMARKET_OFFICIAL','CARDMARKET_OFFICIAL_CT_IDENTITY','CARDMARKET_WEB',
  'CARDMARKET_DE_NM_WEB','CARDTRADER_MARKETPLACE'))
 AND (p.source NOT LIKE 'TCGCSV_TCGPLAYER%'
      OR p.failure_detail ~ 'TCGplayer product [0-9]+')
ON CONFLICT (language_code,card_id,variant_id) DO NOTHING;
"""
before=sql("SELECT language_code,source,count(*) FROM tcg_price_cache WHERE language_code IN ('de','en') AND resolution_status='PRICE_FOUND' AND base_eur>0 GROUP BY 1,2 ORDER BY 1,2")
if args.apply:
 sql(setup)
 sql(insert)
report={"mode":"apply" if args.apply else "dry_run","routing_counts":None,"eligible_sources":before.splitlines()}
if args.apply:
 report["routing_counts"]=sql("SELECT language_code,primary_provider,count(*) FROM price_source_routing GROUP BY 1,2 ORDER BY 1,2").splitlines()
with open(args.report,"w") as file:json.dump(report,file,indent=2)
print(json.dumps({"mode":report["mode"],"routes":report["routing_counts"]},ensure_ascii=False))
