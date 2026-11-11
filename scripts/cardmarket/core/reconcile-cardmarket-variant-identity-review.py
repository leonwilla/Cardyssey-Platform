#!/usr/bin/env python3
"""Correct previously merged Cardmarket candidates using explicit per-variant IDs.

The official product feed validates the expansion. The existing Cardyssey
variant_id distinguishes identical names printed under different card numbers.
This does NOT verify language/foil/edition or publish a price.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
from cardmarket_game_profile import load_game_profile
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path('/home/tv/cardshop')
FEED=load_game_profile()['product_url']
PRODUCTS=Path('/home/tv/.local/state/cardyssey-queue/price-feeds')/(hashlib.sha256(FEED.encode()).hexdigest()+'.json')

def reconcile(apply=False):
 products=json.loads(PRODUCTS.read_text(encoding='utf-8'))['products']
 # Only IDs actually carried by a Cardyssey physical variant, not every
 # similarly named candidate in the product catalog.
 query="""SELECT DISTINCT v->>'cardmarketProductId' FROM catalog_cards_mirror c
 CROSS JOIN LATERAL jsonb_array_elements(c.variants) v
 WHERE c.language_code IN ('de','en')
 AND v->>'cardmarketProductId' ~ '^[0-9]{3,12}$';"""
 cmd=['docker','exec','cardyssey-db','psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','cardyssey','-d','cardyssey']
 p=subprocess.run(cmd+['-c',query],text=True,capture_output=True,check=True,timeout=60)
 variant_ids=set(p.stdout.split())
 catalog={str(x['idProduct']):str(x['idExpansion']) for x in products if str(x['idProduct']) in variant_ids}
 vals=','.join("('%s','%s')"%(pid,exp) for pid,exp in sorted(catalog.items()))
 if not vals:raise RuntimeError('no official product IDs')
 sql="""BEGIN;
 CREATE TEMP TABLE cm_official_variant_product (id TEXT PRIMARY KEY, expansion TEXT) ON COMMIT DROP;
 INSERT INTO cm_official_variant_product(id,expansion) VALUES """+vals+""";
 WITH exact AS (
 SELECT r.language_code,r.card_id,r.variant_id,v.value->>'cardmarketProductId' product_id
 FROM cardmarket_print_identity_review r
 JOIN catalog_cards_mirror c ON c.language_code=r.language_code AND c.card_id=r.card_id
 CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
 JOIN cm_official_variant_product p ON p.id=v.value->>'cardmarketProductId'
 WHERE v.value->>'id'=r.variant_id
 AND r.status='PENDING_REVIEW'
 AND p.expansion=r.provider_expansion_id
 AND (r.matched_set_ids<>jsonb_build_array(p.id) OR r.candidate_ids<>jsonb_build_array(p.id))
 ), updated AS (
 UPDATE cardmarket_print_identity_review r
 SET candidate_ids=jsonb_build_array(e.product_id),matched_set_ids=jsonb_build_array(e.product_id),
 classification='CATALOG_VARIANT_ID_PRINT_PENDING',
 product_names='Exact Cardyssey variant product ID; language/print still pending',
 checked_at=NOW()
 FROM exact e WHERE r.language_code=e.language_code AND r.card_id=e.card_id
 AND r.variant_id=e.variant_id RETURNING r.language_code,r.card_id,r.variant_id
 )
 SELECT json_build_object('corrected',count(*),'de',count(*) FILTER(WHERE language_code='de'),
 'en',count(*) FILTER(WHERE language_code='en'))::text FROM updated;
 -- Reconcile stale official-name-only SOURCE_ONLY routes only when an exact
 -- physical variant ID and its official product expansion agree.
 WITH exact_route AS (
 SELECT r.language_code,r.card_id,r.variant_id,p.id AS product_id
 FROM price_source_routing r
 JOIN catalog_cards_mirror c ON c.language_code=r.language_code AND c.card_id=r.card_id
 CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
 JOIN cm_official_variant_product p ON p.id=v.value->>'cardmarketProductId'
 JOIN cardmarket_catalog_link_candidates k ON k.language_code='de' AND k.card_id=c.card_id
 WHERE v.value->>'id'=r.variant_id
   AND p.expansion=k.provider_expansion_id
   AND r.primary_provider='CARDMARKET' AND r.verification_state='SOURCE_ONLY'
   AND r.source_evidence LIKE 'Official catalogue:%'
   AND r.provider_product_id IS DISTINCT FROM p.id
 ), updated_route AS (
 UPDATE price_source_routing r SET provider_product_id=e.product_id,provider_product_url=NULL,
 source_evidence='Official Cardyssey variant-specific Cardmarket product ID in matched expansion; print and language unverified',
 updated_at=NOW(),next_attempt_at=NOW()
 FROM exact_route e
 WHERE r.language_code=e.language_code AND r.card_id=e.card_id AND r.variant_id=e.variant_id
 RETURNING r.language_code
 )
 SELECT json_build_object('sourceOnlyRoutesCorrected',count(*))::text FROM updated_route;
 """+('COMMIT;' if apply else 'ROLLBACK;')
 out=subprocess.run(['docker','exec','-i','cardyssey-db','psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','cardyssey','-d','cardyssey'],input=sql,capture_output=True,text=True,timeout=120)
 if out.returncode:raise RuntimeError(out.stderr[-950:])
 responses=[json.loads(line) for line in out.stdout.splitlines() if line.startswith('{')]
 result={}
 for response in responses:result.update(response)
 return {'applied':apply,'catalogVariants':len(variant_ids),'officialProducts':len(catalog),**result}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');args=a.parse_args()
 print(json.dumps(reconcile(args.apply),ensure_ascii=False))
