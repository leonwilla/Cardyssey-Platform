#!/usr/bin/env python3
"""Recover Korean Pokemon identities whose imported German species field is absent.

Only parsed records from the already imported, pinned official-source cache are
read. Independent PokeAPI Korean/English/German names establish the species.
No trainer-name substring, source-revision mismatch or ambiguous print is used.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

CACHE = Path("/home/tv/.cache/cardyssey-catalog/source")
NAMES_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon_species_names.csv"

def verified_species(row, raw, revision, names, normalize):
    if row.get("language_code") != "ko" or row.get("identity_count") != 1:
        return None
    url = row.get("source_url") or ""
    m = re.fullmatch(r"https://pokemoncard\.co\.kr/cards/detail/([A-Za-z0-9]+)", url)
    if not m or row.get("source_revision") != revision:
        return None
    if row.get("card_id") != "official_ko_" + hashlib.sha256(url.encode()).hexdigest()[:24]:
        return None
    if raw.get("url") != url or raw.get("ko_id") != m[1] or raw.get("lang") != "ko":
        return None
    if raw.get("name") != row.get("native_name") or raw.get("img") != row.get("image_source_url"):
        return None
    if raw.get("set_name") != row.get("set_id") or str(raw.get("number")) != row.get("local_id"):
        return None
    if raw.get("rarity") != row.get("rarity") or not str(raw.get("set_total","")).isdigit() or int(raw["set_total"]) <= 0:
        return None
    # Older raw records retain localized Pokemon subtypes instead of a unified
    # card_type. Require the Pokemon label and gameplay structure together.
    ctype = str(raw.get("card_type", ""))
    if not (ctype in ("Pokémon","기본","1진화","2진화","V진화","M진화","BREAK진화") or "포켓몬" in ctype) or any(x in ctype for x in ("아이템", "서포트", "스타디움", "에너지")):
        return None
    if type(raw.get("hp")) is not int or raw["hp"] <= 0 or not isinstance(raw.get("attacks"),list) or not raw["attacks"]:
        return None
    hits = [n for n in names if normalize(n["3"]) in normalize(row["native_name"])]
    if not hits:
        return None
    hits = [n for n in hits if len(n["3"]) == max(len(x["3"]) for x in hits)]
    return hits[0] if len(hits) == 1 else None

def load_targets(ko, source, names):
    sql = """WITH counts AS (
      SELECT set_id,LTRIM(local_id,'0') num,COUNT(*) identity_count
      FROM catalog_cards_mirror WHERE language_code='ko' GROUP BY set_id,LTRIM(local_id,'0'))
    SELECT COALESCE(jsonb_agg(to_jsonb(t)),'[]') FROM (
      SELECT c.card_id,c.language_code,c.set_id,c.local_id,c.raw_payload->>'name' native_name,
        c.image_source_url,c.variants old_variants,c.rarity,counts.identity_count,
        p.updated_at old_updated,p.resolution_status old_status,
        s.source_url,s.source_revision
      FROM catalog_cards_mirror c
      JOIN counts ON counts.set_id=c.set_id AND counts.num=LTRIM(c.local_id,'0')
      LEFT JOIN tcg_price_cache p ON p.card_id=c.card_id AND p.language_code='ko' AND p.variant_id='generated'
      JOIN LATERAL (
        SELECT MIN(source_url) source_url,MIN(source_revision) source_revision
        FROM catalog_supplemental_cards s WHERE s.canonical_card_id=c.card_id AND s.language_code='ko'
        HAVING COUNT(DISTINCT source_url)=1 AND COUNT(DISTINCT source_revision)=1
          AND COUNT(DISTINCT german_species_name)=0
      ) s ON TRUE
      WHERE c.language_code='ko' AND c.details_complete AND c.local_id ~ '^[0-9]+$'
        AND c.card_id LIKE 'official_ko_%' AND counts.identity_count=1
        AND c.set_id ~* '^(SM|SV|S|XY|M)[0-9]+[A-Za-z]*$'
        AND (jsonb_array_length(c.variants)=0 OR
          (c.variants=VARIANTS::jsonb AND c.raw_payload->>'_cardyssey_retail_variant_source'=SOURCE))
        AND (p.card_id IS NULL OR p.resolution_status='NO_PRICE' OR p.source=SOURCE)
    ) t"""
    sql = sql.replace("VARIANTS",ko.retail.quote(json.dumps([ko.VARIANT]))).replace("SOURCE",ko.retail.quote(source))
    rows = json.loads(ko.retail.db(sql))
    revision = subprocess.run(["git","-C",str(CACHE),"rev-parse","HEAD"],check=True,text=True,capture_output=True).stdout.strip()
    needed = {r["source_url"] for r in rows}
    records = {}
    duplicates = set()
    for file in (CACHE / "data_ko").rglob("*.json"):
        raw = json.loads(file.read_text())
        url = raw.get("url")
        if url not in needed:
            continue
        if url in records:
            duplicates.add(url)
        records[url] = raw
    verified = []
    for row in rows:
        if row["source_url"] in duplicates:
            continue
        raw = records.get(row["source_url"], {})
        species = verified_species(row,raw,revision,names,ko.normalize)
        if species is None:
            continue
        row.update(german_species=species["6"],official_count=int(raw["set_total"]),
                   species_identity_method="pinned official Korean Pokemon record plus independent PokeAPI Korean/English/German species",
                   species_names_url=NAMES_URL)
        verified.append(row)
    return verified
