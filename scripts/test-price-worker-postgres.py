#!/usr/bin/env python3
"""Run the actual worker upsert SQL against rollback-only PostgreSQL fixtures."""
import json,re,subprocess
from pathlib import Path
source=Path("platform/api/src/main/kotlin/de/cardyssey/api/TcgPriceCache.kt").read_text()
body=source[source.index("    fun write("):source.index("    fun deferExistingPrice(")]
sql=re.search(r'"""(.*?)"""',body,re.S)[1]
assert "normalized != null && written > 0" in body
values=["'card'","'ja'","'variant'","'NORMAL'","'NEW'", "2", "'PRICE_FOUND'", "NULL", "168"]
setup="""CREATE TEMP TABLE tcg_price_cache(card_id text,language_code text,variant_id text,legacy_variant text,source text,base_eur numeric,resolution_status text,failure_detail text,updated_at timestamptz,next_attempt_at timestamptz,UNIQUE(card_id,language_code,variant_id));"""
for label,existing,allow,expected in [
 ("fill_missing","",False,dict(source="NEW",base=2)),
 ("preserve_positive","INSERT INTO tcg_price_cache VALUES('card','ja','variant','NORMAL','OLD',5,'PRICE_FOUND','proof',NOW(),NOW());",False,dict(source="OLD",base=5)),
 ("preserve_inconsistent_positive","INSERT INTO tcg_price_cache VALUES('card','ja','variant','NORMAL','OLD',5,'NO_PRICE','proof',NOW(),NOW());",False,dict(source="OLD",base=5)),
 ("weekly_refresh","INSERT INTO tcg_price_cache VALUES('card','ja','variant','NORMAL','OLD',5,'PRICE_FOUND','proof',NOW(),NOW());",True,dict(source="NEW",base=2))]:
 parts=sql.split("?");assert len(parts)==11
 bindings=values+["TRUE" if allow else "FALSE"]
 statement=parts[0]+"".join(v+p for v,p in zip(bindings,parts[1:]))
 command=["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-X","-qAt","-v","ON_ERROR_STOP=1"]
 query="BEGIN;"+setup+existing+statement+";SELECT jsonb_build_object('source',source,'base',base_eur) FROM tcg_price_cache;ROLLBACK;"
 result=subprocess.run(command,input=query,text=True,capture_output=True,check=True,timeout=25)
 assert json.loads(result.stdout.strip())==expected,(label,result.stdout)
 print("PASS worker SQL",label)
