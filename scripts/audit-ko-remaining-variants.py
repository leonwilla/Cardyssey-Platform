#!/usr/bin/env python3
"""Classify Korean cards still without variants using pinned official source records."""
import csv,json,collections,subprocess
from pathlib import Path
ROOT=Path("/home/tv/.cache/cardyssey-catalog/source/data_ko")
OUTPUT=Path("/home/tv/cardshop/korean-remaining-variant-worklist.csv")
query="""COPY (SELECT c.card_id,c.set_id,c.local_id,c.raw_payload->>'name' AS native_name,c.rarity,c.image_source_url,COALESCE(q.status,'UNQUEUED') AS existing_status
FROM catalog_cards_mirror c LEFT JOIN catalog_variant_reconstruction_queue q ON q.card_id=c.card_id AND q.language_code=c.language_code
WHERE c.language_code='ko' AND c.variants='[]'::jsonb ORDER BY c.set_id,c.local_id) TO STDOUT WITH CSV HEADER"""
p=subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-q","-c",query],capture_output=True,text=True,check=True)
import io
rows=list(csv.DictReader(io.StringIO(p.stdout)))
cache=collections.defaultdict(list)
for folder in ROOT.iterdir():
 if not folder.is_dir():continue
 for file in folder.glob("*.json"):
  try:r=json.loads(file.read_text())
  except (ValueError,OSError):continue
  key=(folder.name.casefold(),str(r.get("number","")).lstrip("0") or "0")
  cache[key].append(r)
stats=collections.Counter()
with OUTPUT.open("w",newline="") as f:
 writer=csv.writer(f)
 writer.writerow(["card_id","set_id","local_id","native_name","queue_status","classification","official_records","official_images","source_rarities","source_urls"])
 for c in rows:
  key=(c["set_id"].casefold(),c["local_id"].lstrip("0") or "0")
  hits=cache.get(key,[])
  names={x.get("name") for x in hits if x.get("name")}
  verified=[x for x in hits if x.get("name")==c["native_name"]]
  imgs={x.get("img") for x in verified if x.get("img")}
  rarities={x.get("rarity") for x in verified if x.get("rarity")}
  if not hits:kind="OFFICIAL_SOURCE_MISSING"
  elif not verified:kind="SOURCE_NAME_MISMATCH"
  elif len(imgs)>1:kind="MULTIPLE_OFFICIAL_PRINT_IMAGES"
  elif len(verified)>1:kind="MULTIPLE_OFFICIAL_RECORDS"
  elif len(rarities)==1:kind="RARITY_PRESENT_IN_SOURCE_RECHECK"
  elif not imgs:kind="NO_OFFICIAL_IMAGE"
  else:kind="SINGLE_IMAGE_PRINTING_UNVERIFIED"
  stats[kind]+=1
  writer.writerow([c["card_id"],c["set_id"],c["local_id"],c["native_name"],c["existing_status"],kind,len(verified),len(imgs),";".join(sorted(rarities)),";".join(sorted(x.get("url","") for x in verified))])
print(json.dumps({"cards":len(rows),"classifications":stats,"worklist":str(OUTPUT)},ensure_ascii=False))
