#!/usr/bin/env python3
"""Persist unresolved pricing search diagnostics after a provider run.

Use --report from refresh-cardmarket-price-cache.py; never invent product
prices or mark product candidates as language/printing verified.
"""
import argparse,json,subprocess
from pathlib import Path

def quote(v):return str(v).replace("'","''")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--report",type=Path,required=True)
 p.add_argument("--apply",action="store_true")
 a=p.parse_args()
 rows=json.loads(a.report.read_text()).get("unresolved",[])
 payload=[]
 for r in rows:
  if not all(r.get(k) for k in ("language","card_id","variant_id","status")):continue
  candidates=[dict(**product,match_type="SET_VERIFIED_PRODUCT") for product in r.get("products") or []]
  candidates += [dict(**product,match_type="NAME_ONLY_WRONG_OR_UNVERIFIED_SET") for product in r.get("name_only_search_hints") or []]
  candidates += [dict(provider=provider,provider_id=identifier,match_type="EXACT_VARIANT_EXTERNAL_ID_NOT_PRICE_PROOF")
                 for provider,identifier in sorted((r.get("exact_variant_provider_ids") or {}).items())]
  reason=", ".join(r.get("unverified_identity_fields") or []) or r["status"]
  if not r.get("set_verified") and r.get("name_only_match_count"):
   reason="KEIN SET-TREFFER; "+str(r["name_only_match_count"])+" Namensähnlichkeiten aus fremden/unbestätigten Sets. "+reason
  if r.get("exact_variant_provider_ids"):
   reason += "; exakte Provider-ID vorhanden, Preis/Edition weiterhin unbestätigt"
  payload.append(dict(language_code=r["language"],card_id=r["card_id"],variant_id=r["variant_id"],
                      search_status=r["status"],search_query=r.get("search_query",""),
                      search_steps=r.get("lookup_steps",[]),candidates=candidates,
                      failure_reason=reason))
 print(f"cases={len(payload)} apply={a.apply}",flush=True)
 if not a.apply:return
 s=json.dumps(payload,ensure_ascii=False)
 sql=f"""
WITH input AS (SELECT jsonb_array_elements('{quote(s)}'::jsonb) AS x)
INSERT INTO price_review_cases
(language_code,card_id,variant_id,search_status,search_query,search_steps,candidates,failure_reason,checked_at)
SELECT x->>'language_code',x->>'card_id',x->>'variant_id',x->>'search_status',
       x->>'search_query',x->'search_steps',x->'candidates',x->>'failure_reason',NOW()
FROM input
ON CONFLICT(language_code,card_id,variant_id) DO UPDATE SET
 search_status=EXCLUDED.search_status,search_query=EXCLUDED.search_query,
 search_steps=EXCLUDED.search_steps,candidates=EXCLUDED.candidates,
 failure_reason=EXCLUDED.failure_reason,checked_at=NOW();
"""
 subprocess.run(["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],
                input=sql,text=True,check=True,stdout=subprocess.DEVNULL)
 print(f"saved={len(payload)}")
if __name__=="__main__":main()
