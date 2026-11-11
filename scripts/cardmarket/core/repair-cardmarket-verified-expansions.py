#!/usr/bin/env python3
"""Repair explicitly verified Cardyssey=>Cardmarket SET links only.

Recomputes product candidates from official Cardmarket catalog INSIDE the
confirmed expansion, preserving ambiguity between physical V1/V2 prints.
Does not touch prices, human verified routes, or confirmed review decisions.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
from cardmarket_game_profile import load_game_profile
import argparse,collections,hashlib,json,subprocess,csv,os
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path('/home/tv/cardshop')
URL=load_game_profile()['product_url']
FEEDS=Path('/home/tv/.local/state/cardyssey-queue/price-feeds')
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')

def sql_quote(x):return "'"+str(x).replace("'","''")+"'"
def pg(sql):
 p=subprocess.run(['docker','exec','-i','cardyssey-db','psql','-X','-v','ON_ERROR_STOP=1','-U','cardyssey','-d','cardyssey'],input=sql,text=True,capture_output=True,timeout=80)
 if p.returncode:raise RuntimeError(p.stderr[-850:])
 return p.stdout

def build(selected):
 spec=spec_from_file_location('mapper',ROOT/'scripts/cardmarket/core/map-all-de-cardmarket-catalog.py')
 m=module_from_spec(spec);spec.loader.exec_module(m)
 data=json.loads((FEEDS/(hashlib.sha256(URL.encode()).hexdigest()+'.json')).read_text())
 products=data['products'];by=collections.defaultdict(list)
 for p in products:
  if str(p.get('idExpansion'))==selected:by[m.sem_name(p.get('name'))].append(p)
 q="SELECT COALESCE(jsonb_agg(to_jsonb(t)),'[]'::jsonb)::text FROM (SELECT card_id,set_id,local_id,name FROM catalog_cards_mirror WHERE language_code='en' AND set_id="+sql_quote(SET)+")t;"
 output=subprocess.run(['docker','exec','cardyssey-db','psql','-X','-qAt','-U','cardyssey','-d','cardyssey','-c',q],capture_output=True,text=True,check=True)
 return [{'card':r['card_id'],'name':r['name'],'ids':sorted({str(x['idProduct']) for x in by.get(m.sem_name(r['name']),[])})} for r in json.loads(output.stdout)]

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--set',required=True);ap.add_argument('--apply',action='store_true');a=ap.parse_args();SET=a.set
 overrides=json.loads((ROOT/'config/cardmarket-verified-set-overrides.json').read_text())
 if SET not in overrides:raise SystemExit('set has no independently confirmed expansion')
 expansion=str(overrides[SET]['expansionId']);rows=build(expansion)
 if len(rows)<3:raise RuntimeError('insufficient known set cards')
 info={'set':SET,'expansion':expansion,'cards':len(rows),'single':sum(len(x['ids'])==1 for x in rows),'multiple':sum(len(x['ids'])>1 for x in rows),'missing':sum(len(x['ids'])==0 for x in rows),'applied':a.apply}
 if a.apply:
  payload=sql_quote(json.dumps(rows,ensure_ascii=False,separators=(',',':')))
  script=f"""BEGIN;
WITH incoming AS (SELECT j->>'card' card,j->'ids' ids,j->>'name' name FROM jsonb_array_elements({payload}::jsonb) j)
UPDATE cardmarket_catalog_link_candidates c SET provider_expansion_id={sql_quote(expansion)},provider_product_ids=i.ids,
 candidate_status=CASE WHEN jsonb_array_length(i.ids)=0 THEN 'NAME_NOT_FOUND_IN_VERIFIED_SET'
 WHEN jsonb_array_length(i.ids)=1 THEN 'SINGLE_SET_PRODUCT' ELSE 'MULTIPLE_SET_PRODUCTS' END,
 checked_at=NOW() FROM incoming i WHERE c.card_id=i.card AND c.set_id={sql_quote(SET)} AND c.language_code='de';
WITH incoming AS (SELECT j->>'card' card,j->'ids' ids,j->>'name' name FROM jsonb_array_elements({payload}::jsonb) j)
UPDATE cardmarket_print_identity_review r SET provider_expansion_id={sql_quote(expansion)},
 candidate_ids=i.ids,matched_set_ids=i.ids,
 product_names='Set-confirmed Cardmarket expansion; print not independently proven',
 classification=CASE WHEN jsonb_array_length(i.ids)=0 THEN 'NO_PRODUCT_ID'
 WHEN jsonb_array_length(i.ids)=1 THEN 'ONE_PRODUCT_IN_VERIFIED_SET_SPECIAL_PRINT'
 ELSE 'MULTIPLE_PRODUCTS_IN_VERIFIED_SET_SPECIAL_PRINT' END, checked_at=NOW()
 FROM incoming i WHERE r.card_id=i.card AND r.set_id={sql_quote(SET)}
 AND r.language_code IN ('de','en') AND r.status='PENDING_REVIEW';
COMMIT;"""
  pg(script)
  # Strip known-false product identities only for the old catalogue SOURCE_ONLY route.
  # Keep row and fallback provider, but clear unverified Cardmarket product hint.
  q=f"""UPDATE price_source_routing r SET provider_product_id=NULL,provider_product_url=NULL,
 source_evidence='Catalog product identity quarantined after verified expansion correction; print pending',updated_at=NOW()
 FROM cardmarket_catalog_link_candidates l
 WHERE r.language_code='de' AND r.card_id=l.card_id AND l.set_id={sql_quote(SET)}
 AND r.primary_provider='CARDMARKET' AND r.verification_state='SOURCE_ONLY'
 AND r.source_evidence LIKE 'Official catalogue:%';"""
  pg('BEGIN;'+q+'COMMIT;')
  ids={r['card']:r['ids'] for r in rows}
  for lang in ('de','en'):
   path=BASE/f'queue-{lang}.csv'
   with path.open(encoding='utf-8-sig',newline='') as f:
    rd=csv.DictReader(f);fields=list(rd.fieldnames or []);old=list(rd)
   changed=0
   for r in old:
    if r['cardyssey_karte'] not in ids or r.get('routing_state')=='VERIFIED_PRODUCT_ID':continue
    r['cardmarket_ids']=','.join(ids[r['cardyssey_karte']]);r['routing_state']='UNVERIFIED';r['known_url']=''
    if 'catalog_singleton_id' in fields:r['catalog_singleton_id']=''
    if 'catalog_search_name' in fields:r['catalog_search_name']=''
    changed+=1
   tmp=path.with_suffix(path.suffix+'.repair.tmp')
   with tmp.open('w',encoding='utf-8-sig',newline='') as f:
    wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(old)
   os.replace(tmp,path)
   info[lang+'_queue']=changed
 print(json.dumps(info,ensure_ascii=False))
