#!/usr/bin/env python3
"""Add browser observations to admin review cases without treating samples as prices."""
import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

VALID = {"FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE", "NO_CONFIRMED_FILTERED_OFFERS"}

def select_observations(records, worklist):
    allowed = {(r["cardyssey_karte"], r["variante_id"]):
               set(filter(None, (r.get("cardmarket_ids") or "").split(",")))
               for r in worklist}
    refresh_days = {(r["cardyssey_karte"],r["variante_id"]):
                    (7 if str(r.get("scan_tier")) in ("0","1") else
                     14 if str(r.get("scan_tier")) == "2" else 30)
                    for r in worklist}
    prepared = {}
    for r in records:
        key = (str(r.get("card_id") or ""), str(r.get("variant_id") or ""))
        pid = str(r.get("product_id") or "")
        if r.get("status") not in VALID or pid not in allowed.get(key, set()):
            continue
        sample = r.get("sample_median_eur")
        if sample is not None and (not isinstance(sample, (float,int)) or not math.isfinite(sample) or sample <= 0):
            continue
        count = r.get("de_nm_offers")
        if not isinstance(count, int) or count < 0 or count > 100:
            continue
        prepared[key] = {
            "language_code": "de", "card_id": key[0], "variant_id": key[1],
            "refresh_days":refresh_days[key],
            "query": str(r.get("query") or "")[:255],
            "candidate": {"provider": "CARDMARKET", "product_id": pid,
                          "match_type": "CARDMARKET_FILTERED_ASKING_SAMPLE",
                          "language": "de", "min_condition": "NM",
                          "sample_count": count, "sample_median_eur": sample,
                          "sample_not_market_wide": True,
                          "no_verified_print_identity": True,
                          "url": str(r.get("url") or "")[:500]}
        }
    return list(prepared.values())

def sql_for(rows):
    serialized = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).replace("'", "''")
    return """
WITH incoming AS (
 SELECT jsonb_array_elements('""" + serialized + """'::jsonb) AS data
), prepared AS (
 SELECT data->>'language_code' AS language_code,
 data->>'card_id' AS card_id, data->>'variant_id' AS variant_id,
 data->>'query' AS search_query, data->'candidate' AS candidate
 FROM incoming
)
INSERT INTO price_review_cases(language_code,card_id,variant_id,search_status,search_query,search_steps,candidates,failure_reason,checked_at)
SELECT language_code,card_id,variant_id,'CARDMARKET_BROWSER_REVIEW',search_query,
 '["CARDMARKET_BROWSER","DE_NM_FILTER"]'::jsonb,
 jsonb_build_array(candidate),
 'Filtered active asking offers only; exact printing/edition/foil/stamp not independently confirmed',NOW()
FROM prepared
ON CONFLICT(language_code,card_id,variant_id) DO UPDATE SET
 candidates=(SELECT COALESCE(jsonb_agg(c.value), '[]'::jsonb)
             FROM jsonb_array_elements(price_review_cases.candidates) c(value)
             WHERE c.value->>'match_type'<>'CARDMARKET_FILTERED_ASKING_SAMPLE')
           || EXCLUDED.candidates,
 checked_at=NOW();
"""

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--queue", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    if not args.results.exists():
        print("browser_results_missing")
        return
    with args.queue.open(encoding="utf-8-sig", newline="") as f:
        queue = list(csv.DictReader(f))
    source_bytes = args.results.read_bytes()
    fingerprint = hashlib.sha256(source_bytes).hexdigest()
    state_path = args.results.with_suffix(".imported_sha256")
    if args.apply and state_path.exists() and state_path.read_text().strip() == fingerprint:
        print("browser_results_unchanged")
        return
    records = []
    for line in source_bytes.decode("utf-8-sig").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    ready = select_observations(records, queue)
    print(json.dumps({"browser_records":len(records),
                      "validated_review_candidates":len(ready), "apply":args.apply}))
    if not args.apply or not ready:
        return
    for i in range(0, len(ready), 100):
        command = ["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1",
                   "-U","cardyssey","-d","cardyssey","-q"]
        subprocess.run(command, input=sql_for(ready[i:i+100]), check=True,
                       text=True, stdout=subprocess.DEVNULL)
    # Retain the stable product ID and canonical URL for later revisit.
    # SOURCE_ONLY never implies an authenticated, print-verified price.
    for i in range(0,len(ready),100):
        batch=ready[i:i+100]
        payload=json.dumps(batch,ensure_ascii=False,separators=(",", ":")).replace("'", "''")
        routing_sql="""
WITH incoming AS (
 SELECT jsonb_array_elements('""" + payload + """'::jsonb) AS data
), fields AS (
 SELECT data->>'language_code' AS language_code,
        data->>'card_id' AS card_id, data->>'variant_id' AS variant_id,
        data->'candidate'->>'product_id' AS product_id,
        (data->>'refresh_days')::integer AS refresh_days,
        split_part(data->'candidate'->>'url','?',1) AS product_url
 FROM incoming
)
INSERT INTO price_source_routing
(language_code,card_id,variant_id,primary_provider,provider_product_id,
 provider_product_url,source_evidence,verification_state,fallback_provider,
 refresh_days,last_attempt_at,next_attempt_at)
SELECT language_code,card_id,variant_id,'CARDMARKET',product_id,
       product_url,'Authenticated browser; filtered asking sample only',
       'SOURCE_ONLY','TCGCSV_TCGPLAYER',refresh_days,NOW(),
       NOW()+make_interval(days=>refresh_days)
FROM fields
WHERE product_url LIKE 'https://www.cardmarket.com/de/Pokemon/Products/Singles/%'
ON CONFLICT(language_code,card_id,variant_id) DO UPDATE SET
 provider_product_id=CASE
   WHEN price_source_routing.verification_state='VERIFIED_PRODUCT_ID'
   THEN price_source_routing.provider_product_id
   ELSE EXCLUDED.provider_product_id END,
 provider_product_url=CASE
   WHEN price_source_routing.verification_state='VERIFIED_PRODUCT_ID'
   THEN price_source_routing.provider_product_url
   ELSE EXCLUDED.provider_product_url END,
 refresh_days=EXCLUDED.refresh_days,
 next_attempt_at=EXCLUDED.next_attempt_at,
 updated_at=NOW()
WHERE price_source_routing.verification_state<>'VERIFIED_PRODUCT_ID';
"""
        subprocess.run(["docker","exec","-i","cardyssey-db","psql", "-v","ON_ERROR_STOP=1",
                        "-U","cardyssey","-d","cardyssey","-q"],input=routing_sql,
                       text=True,check=True,stdout=subprocess.DEVNULL)
    state_path.write_text(fingerprint + "\n", encoding="utf-8")
    print("review_cases_synced", len(ready))

if __name__ == "__main__":
    main()
