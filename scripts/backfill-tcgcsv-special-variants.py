#!/usr/bin/env python3
"""Backfill verified physical printings that TCGplayer stores outside the card's normal set group.

Every mapping below is an exact, manually verified TCGplayer product identity.
The script never guesses a price across variants.
"""
import argparse
import json
import math
import subprocess
import urllib.request

UA={"User-Agent":"Cardyssey/0.4 special-variant-backfill","Accept":"application/json"}
NEAR_MINT_FACTOR=0.92

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","	","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def fetch_json(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=20) as response:
        return json.load(response)

def positive(v):
    return isinstance(v,(int,float)) and math.isfinite(v) and v>0

def q(v):
    return str(v).replace("'","''")

# card_id -> verified physical matcher(s)
# matcher fields identify a variant already present in catalog_cards_mirror.
MAPPINGS=[
    {"card":"dp1-103","foil":["cosmos","kosmos"],"gid":1539,"pid":177130,"subtype":"Holofoil"},
    {"card":"dp1-112","foil":["cosmos","kosmos"],"gid":2374,"pid":177127,"subtype":"Holofoil"},
    {"card":"dp1-76","foil":["cosmos","kosmos"],"gid":2374,"pid":153231,"subtype":"Holofoil"},
    {"card":"dp1-93","foil":["cosmos","kosmos"],"gid":2374,"pid":177129,"subtype":"Holofoil"},
    {"card":"dp2-109","foil":["cosmos","kosmos"],"gid":2374,"pid":177128,"subtype":"Holofoil"},
    {"card":"dp2-33","foil":["cosmos","kosmos"],"gid":1840,"pid":218608,"subtype":"Holofoil"},
    {"card":"dp3-25","foil":["cosmos","kosmos"],"gid":1840,"pid":117600,"subtype":"Holofoil"},
    {"card":"dp4-16","foil":["cosmos","kosmos"],"gid":1840,"pid":227094,"subtype":"Holofoil"},
    {"card":"dp4-26","foil":["cosmos","kosmos"],"gid":1840,"pid":228152,"subtype":"Holofoil"},

    # Theme/deck-exclusive Cosmos Holo printings. Each mapping is a unique
    # TCGplayer Deck Exclusives product for the exact collector number/card.
    {"card":"dp2-21","foil":["cosmos","kosmos"],"gid":1840,"pid":83734,"subtype":"Holofoil"},
    {"card":"dp3-31","foil":["cosmos","kosmos"],"gid":1840,"pid":219028,"subtype":"Holofoil"},
    {"card":"dp5-20","foil":["cosmos","kosmos"],"gid":1840,"pid":93312,"subtype":"Holofoil"},
    {"card":"dp5-24","foil":["cosmos","kosmos"],"gid":1840,"pid":93313,"subtype":"Holofoil"},
    {"card":"dp6-30","foil":["cosmos","kosmos"],"gid":1840,"pid":125067,"subtype":"Holofoil"},
    {"card":"dp6-37","foil":["cosmos","kosmos"],"gid":1840,"pid":123629,"subtype":"Holofoil"},
    {"card":"dp7-19","foil":["cosmos","kosmos"],"gid":1840,"pid":123196,"subtype":"Holofoil"},
    {"card":"dp7-30","foil":["cosmos","kosmos"],"gid":1840,"pid":125079,"subtype":"Holofoil"},
    {"card":"ex10-27","foil":["cosmos","kosmos"],"gid":1840,"pid":181559,"subtype":"Holofoil"},
    {"card":"ex10-29","foil":["cosmos","kosmos"],"gid":1840,"pid":97708,"subtype":"Holofoil"},
    {"card":"ex7-15","foil":["cosmos","kosmos"],"gid":1840,"pid":97956,"subtype":"Holofoil"},
    {"card":"ex7-20","foil":["cosmos","kosmos"],"gid":1840,"pid":97957,"subtype":"Holofoil"},
    {"card":"ex8-16","foil":["cosmos","kosmos"],"gid":1840,"pid":174493,"subtype":"Holofoil"},
    {"card":"ex8-22","foil":["cosmos","kosmos"],"gid":1840,"pid":43053,"subtype":"Holofoil"},
    {"card":"pl1-28","foil":["cosmos","kosmos"],"gid":1840,"pid":125078,"subtype":"Holofoil"},
    {"card":"pl2-20","foil":["cosmos","kosmos"],"gid":1840,"pid":125052,"subtype":"Holofoil"},
    {"card":"pl3-15","foil":["cosmos","kosmos"],"gid":1840,"pid":95826,"subtype":"Holofoil"},
    {"card":"pl3-35","foil":["cosmos","kosmos"],"gid":1840,"pid":125074,"subtype":"Holofoil"},

    # Pokemon League crosshatch printings. TCGplayer exposes these under the
    # Reverse Holofoil price subtype even though the physical Cardyssey variant
    # is modelled as a League Holo.
    {"card":"dp4-15","foil":["league"],"gid":1539,"pid":164289,"subtype":"Reverse Holofoil"},
    {"card":"dp4-98","foil":["league"],"gid":1539,"pid":123192,"subtype":"Reverse Holofoil"},
    {"card":"dp5-88","foil":["league"],"gid":1539,"pid":164286,"subtype":"Reverse Holofoil"},
    {"card":"dp6-19","foil":["league"],"gid":1539,"pid":162456,"subtype":"Reverse Holofoil"},
    {"card":"dp6-43","foil":["league"],"gid":1539,"pid":145871,"subtype":"Reverse Holofoil"},

    # Battle Academy 2024 holo printings represented as SV promo cards upstream.
    {"card":"svp-105","variant_id":"jr7oetx1mqug9","gid":23520,"pid":556445,"subtype":"Holofoil"},
    {"card":"svp-106","variant_id":"jr7oetx1mqug9","gid":23520,"pid":556443,"subtype":"Holofoil"},
    {"card":"svp-110","variant_id":"jr7oetx1mqug9","gid":23520,"pid":556444,"subtype":"Holofoil"},

    # Victory Cup Battle Road trophy printings. BW29/BW30/BW31 represent
    # 3rd/2nd/1st place respectively, with separate season printings.
    {"card":"bwp-BW29","variant_id":"curated:en:bwp:BW29:battle-road-autumn-2011:third-place","gid":1407,"pid":90355,"subtype":"Holofoil"},
    {"card":"bwp-BW29","variant_id":"curated:en:bwp:BW29:battle-road-autumn-2012:third-place","gid":1407,"pid":96862,"subtype":"Holofoil"},
    {"card":"bwp-BW29","variant_id":"curated:en:bwp:BW29:battle-road-spring-2012:third-place","gid":1407,"pid":96863,"subtype":"Holofoil"},
    {"card":"bwp-BW29","variant_id":"curated:en:bwp:BW29:battle-road-spring-2013:third-place","gid":1407,"pid":96868,"subtype":"Holofoil"},
    {"card":"bwp-BW30","variant_id":"curated:en:bwp:BW30:battle-road-autumn-2012:second-place","gid":1407,"pid":96861,"subtype":"Holofoil"},
    {"card":"bwp-BW30","variant_id":"curated:en:bwp:BW30:battle-road-spring-2012:second-place","gid":1407,"pid":96864,"subtype":"Holofoil"},
    {"card":"bwp-BW30","variant_id":"curated:en:bwp:BW30:battle-road-spring-2013:second-place","gid":1407,"pid":96867,"subtype":"Holofoil"},
    {"card":"bwp-BW31","variant_id":"curated:en:bwp:BW31:battle-road-autumn-2011:first-place","gid":1407,"pid":90353,"subtype":"Holofoil"},
    {"card":"bwp-BW31","variant_id":"curated:en:bwp:BW31:battle-road-autumn-2012:first-place","gid":1407,"pid":96860,"subtype":"Holofoil"},
    {"card":"bwp-BW31","variant_id":"curated:en:bwp:BW31:battle-road-spring-2012:first-place","gid":1407,"pid":96865,"subtype":"Holofoil"},
    {"card":"bwp-BW31","variant_id":"curated:en:bwp:BW31:battle-road-spring-2013:first-place","gid":1407,"pid":96866,"subtype":"Holofoil"},

    # XY Sylveon/Noivern Trainer Kit numbered normal printings.
    {"card":"tk-xy-n-14","variant_id":"generated","gid":1532,"pid":98009,"subtype":"Normal"},
    {"card":"tk-xy-n-21","variant_id":"generated","gid":1532,"pid":98019,"subtype":"Normal"},
    {"card":"tk-xy-sy-23","variant_id":"generated","gid":1532,"pid":97988,"subtype":"Normal"},
    {"card":"tk-xy-sy-26","variant_id":"generated","gid":1532,"pid":97991,"subtype":"Normal"},
    {"card":"dp6-131","foil":["cosmos","kosmos"],"gid":2374,"pid":123195,"subtype":"Holofoil"},
    {"card":"ex9-82","stamp":["professor-program","professorenprogramm"],"gid":2332,"pid":176630,"subtype":"Holofoil"},
    {"card":"hgss1-26","foil":["cosmos","kosmos"],"gid":1840,"pid":125041,"subtype":"Holofoil"},
    {"card":"hgss1-26","foil":["cracked-ice"],"gid":1840,"pid":153261,"subtype":"Holofoil"},
    {"card":"hgss2-13","foil":["cracked-ice"],"gid":2374,"pid":145612,"subtype":"Holofoil"},
    {"card":"hgss4-20","variant_id":"555jb0efopmyclvkikic41","gid":1453,"pid":224195,"subtype":"Holofoil"},
    {"card":"hgss4-20","variant_id":"2fnyg4g5382k6pl1ij0u1km1pdn","gid":1453,"pid":224196,"subtype":"Holofoil"},
    {"card":"sm3-28","foil":["cracked-ice"],"gid":1840,"pid":173088,"subtype":"Holofoil"},
    {"card":"sm3-28","foil":["water-web"],"gid":2374,"pid":216514,"subtype":"Holofoil"},
    {"card":"sm3-76","foil":["cracked-ice"],"gid":1840,"pid":178762,"subtype":"Holofoil"},
    {"card":"sm3-76","foil":["water-web"],"gid":2374,"pid":272816,"subtype":"Holofoil"},

    # Play! Pokemon Prize Pack / Player Rewards cosmos printings.
    {"card":"me01-075","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703862,"subtype":"Holofoil"},
    {"card":"me01-101","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":671623,"subtype":"Holofoil"},
    {"card":"me01-116","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703859,"subtype":"Holofoil"},
    {"card":"me01-117","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703858,"subtype":"Holofoil"},
    {"card":"me01-118","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703857,"subtype":"Holofoil"},
    {"card":"me01-119","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703856,"subtype":"Holofoil"},
    {"card":"me01-121","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703855,"subtype":"Holofoil"},
    {"card":"me01-122","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703854,"subtype":"Holofoil"},
    {"card":"me01-124","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703853,"subtype":"Holofoil"},
    {"card":"me01-132","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":671311,"subtype":"Holofoil"},
    {"card":"sv05-024","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":652595,"subtype":"Holofoil"},
    {"card":"sv05-142","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":649175,"subtype":"Holofoil"},
    {"card":"sv05-144","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703819,"subtype":"Holofoil"},
    {"card":"sv05-145","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703820,"subtype":"Holofoil"},
    {"card":"sv05-147","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":565455,"subtype":"Holofoil"},
    {"card":"sv05-148","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":565459,"subtype":"Holofoil"},
    {"card":"sv05-156","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":577585,"subtype":"Holofoil"},
    {"card":"sv05-159","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703828,"subtype":"Holofoil"},
    {"card":"sv09-027","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":648696,"subtype":"Holofoil"},
    {"card":"sv09-047","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":648663,"subtype":"Holofoil"},
    {"card":"sv09-148","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":649184,"subtype":"Holofoil"},
    {"card":"sv09-150","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703848,"subtype":"Holofoil"},
    {"card":"sv09-153","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":703847,"subtype":"Holofoil"},
    {"card":"sv09-154","foil":["cosmos","kosmos"],"stamp":["player-rewards-program"],"gid":22880,"pid":649176,"subtype":"Holofoil"},
]

parser=argparse.ArgumentParser()
parser.add_argument("--dry-run",action="store_true")
args=parser.parse_args()

fx=fetch_json("https://api.frankfurter.dev/v2/rate/USD/EUR").get("rate")
if not positive(fx):
    raise SystemExit("USD/EUR rate unavailable")

groups={}
for mapping in MAPPINGS:
    groups.setdefault(mapping["gid"],None)
for gid in groups:
    rows=fetch_json(f"https://tcgcsv.com/tcgplayer/3/{gid}/prices").get("results") or []
    by={}
    for row in rows:
        try: pid=int(row.get("productId") or 0)
        except (TypeError,ValueError): continue
        by.setdefault(pid,[]).append(row)
    groups[gid]=by

catalog={}
raw=db("""
SELECT card_id,language_code,variants::text
FROM catalog_cards_mirror
WHERE language_code IN ('de','en')
  AND card_id IN (%s)
ORDER BY card_id,language_code
""" % ",".join("'"+q(x)+"'" for x in sorted({m["card"] for m in MAPPINGS})))
for line in raw.splitlines():
    parts=line.split("	",2)
    if len(parts)==3:
        catalog[(parts[0],parts[1])]=json.loads(parts[2] or "[]")

updates=[]
for mapping in MAPPINGS:
    candidates=groups[mapping["gid"]].get(mapping["pid"],[])
    exact=[x for x in candidates if str(x.get("subTypeName") or "").lower()==mapping["subtype"].lower()]
    if len(exact)!=1:
        print(f"skip price identity {mapping['card']} product={mapping['pid']} rows={len(exact)}")
        continue
    entry=exact[0]
    usd=entry.get("marketPrice")
    if not positive(usd): usd=entry.get("midPrice")
    if not positive(usd):
        print(f"skip no price {mapping['card']} product={mapping['pid']}")
        continue
    eur=round((float(usd)*float(fx))/NEAR_MINT_FACTOR,4)

    for language in ("de","en"):
        variants=catalog.get((mapping["card"],language),[])
        matched=[]
        for variant in variants:
            foil=str(variant.get("foil") or "").lower()
            stamps=[str(x).lower() for x in (variant.get("stamps") or [])]
            if "variant_id" in mapping and str(variant.get("id") or "") != mapping["variant_id"]:
                continue
            if "foil" in mapping and foil not in mapping["foil"]:
                continue
            if "stamp" in mapping and not any(stamp in mapping["stamp"] for stamp in stamps):
                continue
            matched.append(variant)
        if len(matched)!=1:
            print(
                f"skip variant identity {mapping['card']}/{language} "
                f"product={mapping['pid']} matches={len(matched)}"
            )
            continue
        variant=matched[0]
        updates.append({
            "card":mapping["card"],"language":language,"variant":variant["id"],
            "legacy":variant.get("legacyVariant") or "HOLO",
            "gid":mapping["gid"],"pid":mapping["pid"],"subtype":mapping["subtype"],
            "eur":eur,
        })

print(f"mappings={len(MAPPINGS)} safe_updates={len(updates)} usd_eur={fx} dry_run={args.dry_run}")
for x in updates:
    print(
        f"{x['language']} {x['card']} {x['variant']} {x['eur']:.4f} EUR "
        f"group={x['gid']} product={x['pid']} {x['subtype']}"
    )

if args.dry_run:
    raise SystemExit(0)

sql=["BEGIN;"]
for x in updates:
    detail=f"TCGplayer product {x['pid']}; {x['subtype']}; group {x['gid']}"
    sql.append(f"""
INSERT INTO tcg_price_cache
(card_id,language_code,variant_id,legacy_variant,source,base_eur,updated_at,resolution_status,failure_detail,next_attempt_at)
VALUES (
 '{q(x["card"])}','{q(x["language"])}','{q(x["variant"])}','{q(x["legacy"])}',
 'TCGCSV_TCGPLAYER',{x["eur"]:.4f},NOW(),'PRICE_FOUND','{q(detail)}',NOW()+INTERVAL '168 hours'
)
ON CONFLICT (card_id,language_code,variant_id) DO UPDATE SET
 legacy_variant=EXCLUDED.legacy_variant,
 source='TCGCSV_TCGPLAYER',
 base_eur=EXCLUDED.base_eur,
 updated_at=NOW(),
 resolution_status='PRICE_FOUND',
 failure_detail=EXCLUDED.failure_detail,
 next_attempt_at=NOW()+INTERVAL '168 hours';
""")
    sql.append(f"""
INSERT INTO tcg_price_history
(card_id,language_code,variant_id,source,base_eur,captured_at)
VALUES ('{q(x["card"])}','{q(x["language"])}','{q(x["variant"])}','TCGCSV_TCGPLAYER',{x["eur"]:.4f},NOW());
""")
sql.append("COMMIT;")
subprocess.run(
    ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],
    input="\n".join(sql),text=True,check=True
)
print(f"applied={len(updates)}")
