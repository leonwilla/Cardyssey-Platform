#!/usr/bin/env python3
import csv
import json
import math
import os
import re
import statistics
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT="/work"
TARGETS=f"{ROOT}/de_remaining_targets.csv"
OUTPUT=f"{ROOT}/de_justtcg_resolved.csv"
KEY=os.environ.get("JUSTTCG_API_KEY","").strip()
if not KEY:
    raise SystemExit("JUSTTCG_API_KEY missing")

def norm(value):
    return re.sub(r"[^a-z0-9]+","",str(value or "").lower())

def fetch_json(url, headers=None, body=None, attempts=3, timeout=25):
    headers=dict(headers or {})
    for attempt in range(attempts):
        try:
            req=urllib.request.Request(
                url,
                data=body,
                headers=headers,
                method="POST" if body is not None else "GET",
            )
            with urllib.request.urlopen(req,timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body_text=""
            try:
                body_text=error.read().decode("utf-8","replace")[:500]
            except Exception:
                pass
            print(f"http_error={error.code} url={url} body={body_text}",flush=True)
            if attempt+1>=attempts:
                return None
            time.sleep(0.4*(attempt+1))
        except Exception as error:
            print(f"request_error={type(error).__name__} url={url}",flush=True)
            if attempt+1>=attempts:
                return None
            time.sleep(0.4*(attempt+1))
    return None

configured_rate=os.environ.get("USD_TO_EUR","").strip()
if configured_rate:
    USD_TO_EUR=float(configured_rate)
else:
    rate_payload=fetch_json("https://api.frankfurter.app/latest?from=USD&to=EUR")
    rate=((rate_payload or {}).get("rates") or {}).get("EUR")
    if not isinstance(rate,(int,float)):
        raise SystemExit("USD/EUR rate unavailable")
    USD_TO_EUR=float(rate)

with open(TARGETS,encoding="utf-8",newline="") as fh:
    target_rows=list(csv.DictReader(fh))
by_card={}
for row in target_rows:
    by_card.setdefault(row["card_id"],[]).append(row)

def fetch_card(card_id):
    payload=fetch_json(f"https://api.tcgdex.net/v2/de/cards/{urllib.parse.quote(card_id)}")
    return card_id,payload

cards={}
card_ids=sorted(by_card)
with ThreadPoolExecutor(max_workers=8) as pool:
    for idx,(card_id,payload) in enumerate(pool.map(fetch_card,card_ids),1):
        cards[card_id]=payload
        if idx%100==0 or idx==len(card_ids):
            print(f"tcgdex={idx}/{len(card_ids)}",flush=True)

lookups=[]
for card_id,rows in by_card.items():
    card=cards.get(card_id)
    if not card:
        continue
    details=card.get("variants_detailed") or []
    variants_by_id={
        str(v.get("variantId") or ""):v
        for v in details
        if str(v.get("variantId") or "")
    }
    for row in rows:
        variant=variants_by_id.get(row["variant_id"])
        if not variant:
            continue
        languages=[str(x).lower() for x in (variant.get("languages") or [])]
        if languages and "de" not in languages:
            continue
        # Generic JustTCG printing families are not precise enough for
        # stamped, subtyped, special-foil or non-standard-size printings.
        if variant.get("stamp"):
            continue
        if str(variant.get("subtype") or "").strip():
            continue
        if str(variant.get("foil") or "").strip():
            continue
        size=str(variant.get("size") or "").strip()
        if size and size.lower()!="standard":
            continue
        tcgplayer=(variant.get("thirdParty") or {}).get("tcgplayer")
        if tcgplayer is None:
            continue
        lookups.append({
            "card_id":card_id,
            "variant_id":row["variant_id"],
            "legacy_variant":row["legacy_variant"].upper(),
            "tcgplayer_id":str(tcgplayer),
        })

# One provider product can be referenced by multiple mirror rows. Fetch each
# product once, then safely map its German near-mint printing family.
unique_ids=sorted({x["tcgplayer_id"] for x in lookups})
print(f"safe_variants={len(lookups)} unique_tcgplayer={len(unique_ids)}",flush=True)

provider={}
headers={
    "x-api-key":KEY,
    "Content-Type":"application/json",
    "Accept":"application/json",
    "User-Agent":"Cardyssey price backfill",
}
for start in range(0,len(unique_ids),20):
    chunk=unique_ids[start:start+20]
    body=json.dumps([{"tcgplayerId":value} for value in chunk]).encode("utf-8")
    payload=fetch_json(
        "https://api.justtcg.com/v1/cards",
        headers=headers,
        body=body,
        attempts=3,
        timeout=30,
    )
    if not payload:
        print(f"batch_failed={start//20+1}",flush=True)
        continue
    for card in payload.get("data") or []:
        value=card.get("tcgplayerId")
        if value is not None:
            provider[str(value)]=card
    metadata=payload.get("_metadata") or {}
    remaining=metadata.get("apiRequestsRemaining")
    print(
        f"justtcg_batch={start//20+1}/{math.ceil(len(unique_ids)/20)} "
        f"received={len(payload.get('data') or [])} remaining={remaining}",
        flush=True,
    )
    time.sleep(0.2)

def printing_matches(printing,family):
    value=norm(printing)
    if family=="REVERSE":
        return "reverse" in value
    if family=="HOLO":
        return "holo" in value and "reverse" not in value
    if family=="NORMAL":
        return "reverse" not in value and "holo" not in value
    return False

resolved=[]
for item in lookups:
    card=provider.get(item["tcgplayer_id"])
    if not card:
        continue
    values=[]
    for variant in card.get("variants") or []:
        language=norm(variant.get("language") or "English")
        if language!=norm("German"):
            continue
        condition=norm(variant.get("condition"))
        if condition not in ("nearmint","nm") and "nearmint" not in condition:
            continue
        if not printing_matches(variant.get("printing"),item["legacy_variant"]):
            continue
        price=variant.get("price")
        if isinstance(price,(int,float)) and math.isfinite(price) and price>0:
            values.append(float(price))
    if not values:
        continue
    usd=statistics.median(values)
    # Existing Cardyssey pricing stores a MINT base and derives NM with 0.90.
    base_eur=(usd*USD_TO_EUR)/0.90
    if math.isfinite(base_eur) and base_eur>0:
        resolved.append({
            **item,
            "base_eur":round(base_eur,4),
            "source":"JUSTTCG",
        })

with open(OUTPUT,"w",encoding="utf-8",newline="") as fh:
    writer=csv.DictWriter(
        fh,
        fieldnames=["card_id","variant_id","legacy_variant","tcgplayer_id","base_eur","source"],
    )
    writer.writeheader()
    writer.writerows(resolved)

print(f"resolved={len(resolved)} output={OUTPUT}",flush=True)
