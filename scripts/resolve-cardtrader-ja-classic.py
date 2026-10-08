#!/usr/bin/env python3
import json,re,statistics,subprocess,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"
NM_FACTOR=0.92
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="):
        TOKEN=line.split("=",1)[1].strip(); break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-ja-classic"}

def get(url,timeout=30):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code!=429 or attempt==2:
                raise
            retry_after=e.headers.get("Retry-After")
            try: delay=float(retry_after)
            except (TypeError,ValueError): delay=0.75*(attempt+1)
            time.sleep(min(max(delay,0.5),3.0))
def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()
def q(v): return str(v).replace("'","''")
def num(v):
    s=str(v or "").strip().lower().split("/",1)[0].strip()
    if s.isdigit(): return str(int(s))
    return re.sub(r"^0+(?=\d)","",s)

SET_CODE={
    "E1":"ec1","E2":"ec2","E3":"ec3","E4":"ec4","E5":"ec5",
    "PCG1":"fol","PCG2":"cbs","PCG3":"rgsb","PCG4":"gsso",
    "PCG5":"mif","PCG6":"hrt","PCG7":"hof","PCG8":"mic","PCG9":"odffe",
    "VS1":"pvs","web1":"pwe",
}
expansions=[e for e in get(f"{BASE}/expansions") if int(e.get("game_id") or 0)==5]
by_code={str(e.get("code") or "").lower():e for e in expansions}

raw=db("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,p.legacy_variant,v.value::text,c.variants::text
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='ja' AND p.resolution_status='NO_PRICE'
  AND v.value->>'id'=p.variant_id
ORDER BY c.set_id,c.local_id""")
rows=[]
for line in raw.splitlines():
    z=line.split("\t",7)
    if len(z)!=8: continue
    cid,setid,local_id,name,vid,legacy,vjson,all_variants_json=z
    try:v=json.loads(vjson)
    except Exception:continue
    if legacy not in ("NORMAL","HOLO"): continue
    if v.get("foil") or str(v.get("size") or "").lower() not in ("","standard"): continue
    stamps=[str(x).lower() for x in (v.get("stamps") or [])]
    subtype=str(v.get("subtype") or "").lower()

    expected_first=None
    code=SET_CODE.get(setid)
    if any("1st" in x for x in stamps):
        expected_first=True
    elif subtype=="unlimited":
        expected_first=False
    elif setid=="PMCG1" and subtype=="no-rarity":
        code="1epnr"
        expected_first=False
    elif setid in ("VS1","web1") and not stamps and not subtype:
        # Nearly every plain card has a matching 1st-edition variant in our
        # catalog, so the plain printing is the non-1st-edition counterpart.
        expected_first=False
    elif not stamps and not subtype:
        # Some early Japanese sets encode the unlimited counterpart as a
        # plain variant instead of subtype=unlimited. Accept it only when the
        # same card also has a 1st-edition variant and has no explicit
        # unlimited variant, which makes the pairing unambiguous.
        all_variants=json.loads(all_variants_json or "[]")
        has_1st=any(
            any("1st" in str(s).lower() for s in (item.get("stamps") or []))
            for item in all_variants
        )
        has_unlimited=any(
            str(item.get("subtype") or "").lower()=="unlimited"
            for item in all_variants
        )
        if has_1st and not has_unlimited:
            expected_first=False
        else:
            continue
    else:
        continue

    e=by_code.get(str(code or "").lower())
    if not e: continue
    rows.append({
        "card_id":cid,"set_id":setid,"local_id":local_id,"name":name,
        "variant_id":vid,"legacy":legacy,"expected_first":expected_first,
        "expansion_id":int(e["id"]),"expansion_code":code,
    })

print(f"classic_candidates={len(rows)}",flush=True)

blueprints={}
for eid in sorted({r["expansion_id"] for r in rows}):
    try: blueprints[eid]=get(f"{BASE}/blueprints/export?expansion_id={eid}",30)
    except Exception as e:
        print(f"classic_blueprint_error expansion={eid} error={e!r}",flush=True)
        blueprints[eid]=[]

indexes={}
for eid,bps in blueprints.items():
    idx={}
    for b in bps:
        n=num((b.get("fixed_properties") or {}).get("collector_number"))
        if n: idx.setdefault(n,[]).append(b)
    indexes[eid]=idx

resolved=[]
ambiguous=0
for r in rows:
    cand=indexes.get(r["expansion_id"],{}).get(num(r["local_id"]),[])
    if len(cand)!=1:
        if len(cand)>1: ambiguous+=1
        continue
    blueprint=cand[0]
    cmids=[]
    for value in blueprint.get("card_market_ids") or []:
        try: cmids.append(int(value))
        except (TypeError,ValueError): pass
    resolved.append({
        **r,
        "blueprint_id":int(blueprint["id"]),
        "cardmarket_id":cmids[0] if len(cmids)==1 else None,
    })
print(f"classic_resolved={len(resolved)} ambiguous={ambiguous}",flush=True)

# Cache the exact CardTrader blueprint for every resolved physical variant,
# even when Cardmarket has no product id. The blueprint plus the expected
# first-edition flag is still useful provenance for backlog classification.
identity_rows=resolved
if identity_rows:
    values=[]
    for r in identity_rows:
        # Cardmarket product ids are safe only for dedicated no-rarity
        # products. Cardmarket's Japanese product price does not distinguish
        # CardTrader's editable first_edition flag.
        cm=(
            str(r["cardmarket_id"])
            if r["expansion_code"]=="1epnr" and r["cardmarket_id"] is not None
            else "NULL"
        )
        method=(
            "ja-classic-no-rarity"
            if r["expansion_code"]=="1epnr"
            else f"ja-classic-{'1st' if r['expected_first'] else 'unlimited'}"
        )
        values.append(
            f"('{q(r['card_id'])}','ja','{q(r['variant_id'])}',"
            f"{cm},{r['blueprint_id']},{r['expansion_id']},'{method}')"
        )
    for start in range(0,len(values),250):
        chunk=values[start:start+250]
        db(
            "INSERT INTO cardtrader_variant_identity_cache"
            "(card_id,language_code,variant_id,cardmarket_product_id,blueprint_id,expansion_id,method) VALUES "
            + ",".join(chunk)
            + " ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET "
              "cardmarket_product_id=EXCLUDED.cardmarket_product_id,"
              "blueprint_id=EXCLUDED.blueprint_id,"
              "expansion_id=EXCLUDED.expansion_id,"
              "method=EXCLUDED.method,updated_at=NOW()"
        )
print(f"classic_variant_identities={len(identity_rows)}",flush=True)

updates=[]
reasons={"no_products":0,"graded":0,"condition":0,"language":0,"edition":0,"reverse":0,"price":0}

def condition_calibration(payload):
    """Empirically derive NM/lower-condition ratios within one expansion."""
    ratios={"slightly played":[],"moderately played":[],"played":[]}
    for products in payload.values() if isinstance(payload,dict) else []:
        groups={}
        for p in products:
            if p.get("graded"): continue
            props=p.get("properties_hash") or {}
            lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
            if lang and lang!="jp": continue
            rv=next((v for k,v in props.items() if "reverse" in str(k).lower()),None)
            if str(rv).lower() in ("true","1","yes"): continue
            price=p.get("price") or {}; cents=price.get("cents")
            if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR": continue
            try: unit=float(cents)/100.0/max(1,int(p.get("bundle_size") or 1))
            except Exception: continue
            edition=str(props.get("first_edition")).lower() in ("true","1","yes")
            cond=str(props.get("condition") or "").strip().lower()
            groups.setdefault(edition,{}).setdefault(cond,[]).append(unit)
        for conds in groups.values():
            nm=(conds.get("near mint") or [])+(conds.get("mint") or [])
            if not nm: continue
            nm.sort(); nm_med=statistics.median(nm[:min(7,len(nm))])
            for cond in ratios:
                vals=conds.get(cond) or []
                if not vals: continue
                vals=sorted(vals)
                lower_med=statistics.median(vals[:min(7,len(vals))])
                if lower_med<=0: continue
                ratio=nm_med/lower_med
                if 1.0 <= ratio <= 8.0:
                    ratios[cond].append(ratio)
    return {
        cond:(statistics.median(vals),len(vals))
        for cond,vals in ratios.items()
        if len(vals)>=5
    }

def edition_calibration(payload):
    """Median NM first-edition/unlimited ratio from cards having both."""
    ratios=[]
    for products in payload.values() if isinstance(payload,dict) else []:
        editions={True:[],False:[]}
        for p in products:
            if p.get("graded"): continue
            props=p.get("properties_hash") or {}
            lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
            if lang and lang!="jp": continue
            rv=next((v for k,v in props.items() if "reverse" in str(k).lower()),None)
            if str(rv).lower() in ("true","1","yes"): continue
            cond=str(props.get("condition") or "").strip().lower()
            if cond not in ("near mint","mint","nm"): continue
            price=p.get("price") or {}; cents=price.get("cents")
            if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR": continue
            try: unit=float(cents)/100.0/max(1,int(p.get("bundle_size") or 1))
            except Exception: continue
            is_first=str(props.get("first_edition")).lower() in ("true","1","yes")
            editions[is_first].append(unit)
        if editions[True] and editions[False]:
            first=sorted(editions[True]); unlimited=sorted(editions[False])
            first_med=statistics.median(first[:min(7,len(first))])
            unlimited_med=statistics.median(unlimited[:min(7,len(unlimited))])
            if unlimited_med<=0: continue
            ratio=first_med/unlimited_med
            if 0.4<=ratio<=2.5:
                ratios.append(ratio)
    if len(ratios)<10:
        return None
    return statistics.median(ratios),len(ratios)

market_payloads={}
for eid in sorted({r["expansion_id"] for r in resolved}):
    try:
        market_payloads[eid]=get(
            f"{BASE}/marketplace/products?"+urllib.parse.urlencode({"expansion_id":eid}),
            40,
        )
    except Exception as e:
        print(f"classic_market_error expansion={eid} error={e!r}",flush=True)
        market_payloads[eid]={}

# PCG-era first-edition/unlimited prices are unusually consistent across sets.
# Use a cross-set calibration only when >=10 same-card NM pairs support it.
pcg_codes={"fol","cbs","rgsb","gsso","mif","hrt","hof","mic","odffe"}
pcg_eids={
    r["expansion_id"] for r in resolved
    if r["expansion_code"] in pcg_codes
}
pcg_payload={}
for eid in pcg_eids:
    for blueprint_id,products in market_payloads.get(eid,{}).items():
        pcg_payload[f"{eid}:{blueprint_id}"]=products
pcg_edition_cal=edition_calibration(pcg_payload)
if pcg_edition_cal is not None:
    print(
        f"classic_pcg_edition_calibration={pcg_edition_cal[0]:.4f} "
        f"pairs={pcg_edition_cal[1]}",
        flush=True,
    )

for gi,eid in enumerate(sorted({r["expansion_id"] for r in resolved}),1):
    payload=market_payloads.get(eid,{})
    calibration=condition_calibration(payload)
    edition_cal=edition_calibration(payload)
    for r in [x for x in resolved if x["expansion_id"]==eid]:
        products=payload.get(str(r["blueprint_id"]),[]) if isinstance(payload,dict) else []
        if not products: reasons["no_products"]+=1
        nm_values=[]
        sp_values=[]
        mp_values=[]
        played_values=[]
        opposite_nm_values=[]
        for p in products:
            if p.get("graded"): reasons["graded"]+=1; continue
            props=p.get("properties_hash") or {}
            lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
            if lang and lang!="jp": reasons["language"]+=1; continue
            is_first=r["expected_first"]
            if r["expansion_code"]!="1epnr":
                edition=props.get("first_edition")
                is_first=str(edition).lower() in ("true","1","yes")
            rv=next((v for k,v in props.items() if "reverse" in str(k).lower()),None)
            if str(rv).lower() in ("true","1","yes"): reasons["reverse"]+=1; continue
            price=p.get("price") or {}; cents=price.get("cents")
            if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR":
                reasons["price"]+=1; continue
            try: unit=float(cents)/100.0/max(1,int(p.get("bundle_size") or 1))
            except Exception: reasons["price"]+=1; continue
            cond=str(props.get("condition") or "").strip().lower()
            if is_first != r["expected_first"]:
                reasons["edition"]+=1
                if cond in ("near mint","mint","nm"):
                    opposite_nm_values.append(unit)
                continue
            if cond in ("near mint","mint","nm"):
                nm_values.append(unit)
            elif cond=="slightly played":
                sp_values.append(unit)
            elif cond=="moderately played":
                mp_values.append(unit)
            elif cond=="played":
                played_values.append(unit)
            else:
                reasons["condition"]+=1

        values=nm_values
        factor=NM_FACTOR
        source="CARDTRADER_MARKETPLACE"
        condition_label="NM"
        condition_ratio=1.0
        if not values and len(sp_values)>=2 and "slightly played" in calibration:
            values=sp_values
            condition_ratio=calibration["slightly played"][0]
            source="CARDTRADER_SP_INFERRED"
            condition_label=f"SP_INFERRED x{condition_ratio:.3f} ncal={calibration['slightly played'][1]}"
        elif not values and len(sp_values)>=3:
            values=sp_values
            factor=0.80
            source="CARDTRADER_SP_INFERRED"
            condition_label="SP_INFERRED_FIXED"
        elif not values and len(mp_values)>=3 and "moderately played" in calibration:
            values=mp_values
            condition_ratio=calibration["moderately played"][0]
            factor=NM_FACTOR
            source="CARDTRADER_MP_INFERRED"
            condition_label=f"MP_INFERRED x{condition_ratio:.3f} ncal={calibration['moderately played'][1]}"
        elif not values and len(played_values)>=3 and "played" in calibration:
            values=played_values
            condition_ratio=calibration["played"][0]
            factor=NM_FACTOR
            source="CARDTRADER_PLAYED_INFERRED"
            condition_label=f"PLAYED_INFERRED x{condition_ratio:.3f} ncal={calibration['played'][1]}"
        elif not values and len(opposite_nm_values)>=2 and edition_cal is not None:
            values=opposite_nm_values
            edition_ratio,edition_n=edition_cal
            condition_ratio=edition_ratio if r["expected_first"] else (1.0/edition_ratio)
            factor=NM_FACTOR
            source="CARDTRADER_EDITION_INFERRED"
            condition_label=(
                f"EDITION_INFERRED {'1ST' if r['expected_first'] else 'UNLIMITED'} "
                f"x{condition_ratio:.3f} ncal={edition_n}"
            )
        elif (
            not values
            and len(opposite_nm_values)>=2
            and pcg_edition_cal is not None
            and r["expansion_code"] in pcg_codes
        ):
            opposite_sorted=sorted(opposite_nm_values)
            opposite_median=statistics.median(opposite_sorted[:min(7,len(opposite_sorted))])
            # Avoid cross-edition inference for very high-value cards where a
            # modest percentage error would be material.
            if opposite_median<=100.0:
                values=opposite_nm_values
                edition_ratio,edition_n=pcg_edition_cal
                condition_ratio=edition_ratio if r["expected_first"] else (1.0/edition_ratio)
                factor=NM_FACTOR
                source="CARDTRADER_EDITION_INFERRED_PCG"
                condition_label=(
                    f"EDITION_INFERRED_PCG {'1ST' if r['expected_first'] else 'UNLIMITED'} "
                    f"x{condition_ratio:.3f} ncal={edition_n}"
                )
        if values:
            values.sort(); sample=values[:min(7,len(values))]
            listing=round(statistics.median(sample),4)
            base=round((listing*condition_ratio)/factor,4)
            updates.append((r,base,listing,len(values),source,condition_label))
    print(f"classic_market={gi}/{len(set(x['expansion_id'] for x in resolved))} updates={len(updates)}",flush=True)

print("classic_reasons="+json.dumps(reasons,separators=(",",":")),flush=True)
print(f"classic_updates={len(updates)}",flush=True)

if updates:
    sql=["BEGIN;"]
    for r,base,listing,count,source,condition_label in updates:
        detail=f"CardTrader classic {r['expansion_code']} blueprint {r['blueprint_id']}; first_edition={r['expected_first']}; condition={condition_label}; median listing EUR {listing:.4f}; listings {count}"
        sql.append(f"UPDATE tcg_price_cache SET source='{source}',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='ja' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','ja','{q(r['variant_id'])}','{source}',{base:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"classic_applied={len(updates)}",flush=True)
