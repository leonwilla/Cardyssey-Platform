#!/usr/bin/env python3
"""Count uniquely priced catalog cards per set, regardless of cache variants."""
import sys,json,subprocess
language=sys.argv[1]
if language not in ('de','en','ja','ko','zh-cn','zh-tw'):raise SystemExit('unsupported_language')
q="SELECT c.set_id,count(DISTINCT c.card_id) FROM catalog_cards_mirror c JOIN tcg_price_cache p ON p.card_id=c.card_id AND p.language_code=c.language_code AND p.base_eur>0 WHERE c.language_code='"+language+"' GROUP BY c.set_id"
out=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',q],timeout=20,text=True)
print(json.dumps({a:int(b) for line in out.splitlines() if '|' in line for a,b in [line.split('|',1)]}))
