#!/usr/bin/env python3
"""Reuse a verified image source across duplicate mirror rows for the same printing.

Only copies a source when language + set + normalized local id match exactly and
there is exactly one distinct non-null source URL for that identity.
"""
import argparse, subprocess

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

p=argparse.ArgumentParser()
p.add_argument("--apply",action="store_true")
a=p.parse_args()

where="" if a.apply else "AND FALSE"
sql=f"""
WITH src AS (
  SELECT language_code, upper(set_id) set_key,
         COALESCE(NULLIF(ltrim(local_id,'0'),''),'0') local_key,
         min(image_source_url) image_source_url
  FROM catalog_cards_mirror
  WHERE image_source_url IS NOT NULL
  GROUP BY language_code, upper(set_id), COALESCE(NULLIF(ltrim(local_id,'0'),''),'0')
  HAVING count(DISTINCT image_source_url)=1
), candidates AS (
  SELECT c.language_code,c.card_id,src.image_source_url
  FROM catalog_cards_mirror c
  JOIN src ON src.language_code=c.language_code
          AND src.set_key=upper(c.set_id)
          AND src.local_key=COALESCE(NULLIF(ltrim(c.local_id,'0'),''),'0')
  WHERE c.image_source_url IS NULL
)
SELECT count(*) FROM candidates;
"""
count=db(sql)
print(f"candidates={count} applied={a.apply}")
if a.apply:
    updated=db("""
WITH src AS (
  SELECT language_code, upper(set_id) set_key,
         COALESCE(NULLIF(ltrim(local_id,'0'),''),'0') local_key,
         min(image_source_url) image_source_url
  FROM catalog_cards_mirror
  WHERE image_source_url IS NOT NULL
  GROUP BY language_code, upper(set_id), COALESCE(NULLIF(ltrim(local_id,'0'),''),'0')
  HAVING count(DISTINCT image_source_url)=1
)
UPDATE catalog_cards_mirror c
SET image_source_url=src.image_source_url,image_complete=FALSE,image_dhash=NULL,source_updated_at=NOW()
FROM src
WHERE c.language_code=src.language_code
  AND upper(c.set_id)=src.set_key
  AND COALESCE(NULLIF(ltrim(c.local_id,'0'),''),'0')=src.local_key
  AND c.image_source_url IS NULL
RETURNING c.language_code||':'||c.card_id;
""")
    print(updated)
