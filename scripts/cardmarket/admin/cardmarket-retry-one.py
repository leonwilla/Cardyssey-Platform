#!/usr/bin/env python3
"""Prioritize exactly one Cardmarket queue row for another browser pass.
Does not accept/correct product IDs, manipulate prices, or clear observations.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse,csv,fcntl,json,os,re,tempfile
from datetime import datetime,timezone
from pathlib import Path
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
def retry(language,card,variant,base=BASE,now=None):
 if language not in ('de','en') or not re.fullmatch('[a-zA-Z0-9_.-]{1,128}',card) or not re.fullmatch('[a-zA-Z0-9_.-]{1,128}',variant):raise ValueError('invalid_card_identity')
 path=base/f'queue-{language}.csv'
 with (base/f'queue-{language}.review.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  with path.open(encoding='utf-8-sig',newline='') as f:
   r=csv.DictReader(f);fields=list(r.fieldnames or []);rows=list(r)
  if 'manual_scan_requested_at' not in fields:fields.append('manual_scan_requested_at')
  found=0;stamp=(now or datetime.now(timezone.utc)).isoformat()
  for row in rows:
   if row.get('cardyssey_karte')==card and row.get('variante_id')==variant:
    row['manual_scan_requested_at']=stamp;found+=1
  if found!=1:raise ValueError('card_variant_not_in_current_queue')
  fd,tmp=tempfile.mkstemp(prefix='cardmarket-retry-',suffix='.tmp',dir=base)
  try:
   with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
   os.replace(tmp,path)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
 return {'ok':True,'language':language,'cardId':card,'variantId':variant,'priorityScanRequestedAt':stamp}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--language',required=True);p.add_argument('--card',required=True);p.add_argument('--variant',required=True);a=p.parse_args()
 print(json.dumps(retry(a.language,a.card,a.variant),ensure_ascii=False))
