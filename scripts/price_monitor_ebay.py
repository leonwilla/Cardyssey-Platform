#!/usr/bin/env python3
"""Read only eBay monitor. Preserve every batch, prefer most recent results."""
import json,sys,subprocess
from pathlib import Path
root=Path('/home/tv/cardyssey-ebay-collector')
runs=sorted((p for p in root.glob('anniversary-*') if (p/'progress.json').is_file()),key=lambda p:p.stat().st_mtime)
cards={}; results={}
for run in runs:
 manifest=run/'manifest.json'
 if manifest.is_file():
  for c in json.loads(manifest.read_text()):cards[c['card_id']]=c
 state=json.loads((run/'progress.json').read_text())
 for r in state.get('results',[]):
  detail={**r,'run':run.name}
  p=run/r['card_id']/'sales.json'
  if p.is_file():
   report=json.loads(p.read_text())
   detail['query']=report.get('config',{}).get('query') or report.get('query')
   detail['collectorReasons']={}
   from collections import Counter
   reasons=Counter()
   for row in report.get('rows',[]):
    if not row.get('eligible'):
     reasons.update(filter(None,(row.get('exclusions') or '').split(';')))
   detail['collectorReasons']=dict(reasons)
   detail['pages']=report.get('pages',[])
  results[r['card_id']]=detail
sql="SELECT card_id,round(base_eur::numeric,4),sample_count,updated_at FROM ebay_price_cache WHERE language_code='de' AND source='CARDYSSEY_EBAY' AND base_eur>0"
out=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',sql],timeout=12,text=True)
prices={a:(float(b),int(c),t) for line in out.splitlines() if (parts:=line.split('|')) and len(parts)==4 for a,b,c,t in [parts]}
items=[]
for card_id,c in cards.items():
 r=results.get(card_id,{});price=prices.get(card_id)
 items.append({'cardId':card_id,'setId':c['set_id'],'name':c['name'],'number':c['local_id'],'price':price[0] if price else None,'sales':price[1] if price else None,'updatedAt':price[2] if price else None,'status':'PRICE_FOUND' if price else r.get('status','NOT_CHECKED'),'failure':None if price else r.get('status','Noch nicht geprüft'),'searchQuery':r.get('query'),'parsed':r.get('parsed',0),'matched':r.get('nm_candidates',0),'rejections':r.get('rejections',{}),'collectorReasons':r.get('collectorReasons',{}),'run':r.get('run'),'pages':r.get('pages',[])})
catalog_sql="SELECT set_id,count(*) FROM catalog_cards_mirror WHERE language_code='de' AND set_id IN ('30th','30th-c','mep','sv01','sv02') GROUP BY set_id"
catalog_out=subprocess.check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-At','-F','|','-c',catalog_sql],timeout=12,text=True)
catalog_counts={setid:int(count) for line in catalog_out.splitlines() if '|' in line for setid,count in [line.split('|',1)]}
print(json.dumps({'catalogCounts':catalog_counts,'items':items,'runs':[{'name':p.name,'status':json.loads((p/'progress.json').read_text()).get('status')} for p in runs]},ensure_ascii=False))
