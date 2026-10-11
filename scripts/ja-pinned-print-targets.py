#!/usr/bin/env python3
"""Pinned exact Japanese print identities, including rarity-less modern decks."""
import hashlib,json,re,subprocess
from collections import Counter,defaultdict
from pathlib import Path

CACHE=Path("/home/tv/.cache/cardyssey-catalog/source")
MEGA_DECK_CODES={"MA","MBD","MBG","MDB","MEE","MEM","MEZ","MG","MMB-P","MMB-S","MP1"}
PROMO_CODES={"SMP":"SM-P","XYP":"XY-P","S-P":"S-P","SV-P":"SV-P","M-P":"M-P"}

def eligible_code(code):
    return code in PROMO_CODES or code in MEGA_DECK_CODES or re.fullmatch(r"(?:(?:SV|SM|S)[A-Za-z0-9]+|M[0-9]+[A-Za-z]*)",code,re.I) is not None

def verified_record(row,raw,revision,*,require_unique=True):
    url=row.get("official_url","")
    if row.get("language_code")!="ja" or (require_unique and row.get("identity_count")!=1) or not eligible_code(row.get("set_id","")):
        return None
    if not re.fullmatch(r"https://www\.pokemon-card\.com/card-search/details\.php/card/[0-9]+",url):
        return None
    if row.get("source_revision")!=revision or row.get("card_id")!="official_ja_"+hashlib.sha256(url.encode()).hexdigest()[:24]:
        return None
    if raw.get("url")!=url or str(raw.get("jp_id"))!=url.rsplit("/",1)[1]:
        return None
    for raw_key,row_key in [("name","native_name"),("set_name","set_id"),("number","local_id"),("img","image_source_url"),("rarity","rarity")]:
        if raw.get(raw_key)!=row.get(row_key):
            return None
    total=str(raw.get("set_total",""))
    promo=row["set_id"] in PROMO_CODES
    if (promo and total!=PROMO_CODES[row["set_id"]]) or (not promo and (not total.isdigit() or int(total)<=0)):
        return None
    if not row.get("native_name") or not row.get("image_source_url"):
        return None
    return dict(row,printed_code=PROMO_CODES.get(row["set_id"],row["set_id"]),printed_total=total,
                official_number=row["local_id"]+"/"+total,raw_card_type=raw.get("card_type"))

def load_targets(ja,sources,missing_only=False):
    quoted=",".join(ja.retail.quote(s) for s in sources)
    variants=ja.retail.quote(json.dumps([ja.VARIANT]))
    sql="""WITH counts AS (
      SELECT set_id,LTRIM(local_id,'0') num,COUNT(*) identity_count
      FROM catalog_cards_mirror WHERE language_code='ja' GROUP BY set_id,LTRIM(local_id,'0'))
    SELECT COALESCE(jsonb_agg(row_to_json(t)),'[]') FROM (
      SELECT c.card_id,c.language_code,c.set_id,c.local_id,c.rarity,c.raw_payload->>'name' native_name,
        c.image_source_url,c.variants old_variants,p.updated_at old_updated,p.resolution_status old_status,
        counts.identity_count,s.official_url,s.source_revision
      FROM catalog_cards_mirror c JOIN counts ON counts.set_id=c.set_id AND counts.num=LTRIM(c.local_id,'0')
      LEFT JOIN tcg_price_cache p ON p.card_id=c.card_id AND p.language_code='ja' AND p.variant_id='generated'
      JOIN LATERAL (
        SELECT MIN(source_url) official_url,MIN(source_revision) source_revision
        FROM catalog_supplemental_cards s WHERE s.canonical_card_id=c.card_id AND s.language_code='ja'
        HAVING COUNT(DISTINCT source_url)=1 AND COUNT(DISTINCT source_revision)=1
      )s ON TRUE
      WHERE c.language_code='ja' AND c.card_id LIKE 'official_ja_%' AND c.local_id ~ '^[0-9]+$'
        AND c.details_complete AND counts.identity_count=1
        AND (jsonb_array_length(c.variants)=0 OR (c.variants=VARIANTS::jsonb
             AND c.raw_payload->>'_cardyssey_retail_variant_source' IN (SOURCES)))
        AND (p.card_id IS NULL OR p.resolution_status='NO_PRICE' OR p.source IN (SOURCES))
    )t;"""
    rows=json.loads(ja.retail.db(sql.replace("VARIANTS",variants).replace("SOURCES",quoted)))
    if missing_only:
        rows=ja.missing.filter_targets(rows,ja.retail)
    revision=subprocess.run(["git","-C",str(CACHE),"rev-parse","HEAD"],text=True,capture_output=True,check=True).stdout.strip()
    needed={r["official_url"] for r in rows};records=defaultdict(list)
    for file in (CACHE/"data_jp").rglob("*.json"):
        raw=json.loads(file.read_text())
        if raw.get("url") in needed:records[raw["url"]].append(raw)
    result=[];rejected=Counter()
    for row in rows:
        raw=records[row["official_url"]]
        verified=verified_record(row,raw[0],revision) if len(raw)==1 else None
        if verified is None:rejected["pinned_print_unverified"]+=1
        else:result.append(verified)
    return result,dict(rejected)
