#!/usr/bin/env python3
"""Current six-language global price-source coverage for authorized monitoring."""
import json,subprocess

sql="SELECT summary::text FROM global_price_policy_sync WHERE id=1;"
r=subprocess.run(['docker','exec','cardyssey-db','psql','-X','-U','cardyssey','-d','cardyssey','-Atc',sql],capture_output=True,text=True,check=True,timeout=12)
print(json.dumps(json.loads(r.stdout.strip() or '{}'),ensure_ascii=False))
