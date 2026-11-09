#!/usr/bin/env python3
"""Read-only audit: ambiguous Cardyssey/Cardmarket expansion matches.

The official singles product feed has idExpansion but not independently proven
Cardyssey set IDs, numbers, prints or languages. Therefore a shared name list
is an ambiguity, not proof of a wrong mapping. Never auto-reassign products.
"""
import argparse,collections,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
import importlib.util
mapper_spec=importlib.util.spec_from_file_location('cardmarket_mapper',Path(__file__).with_name('map-all-de-cardmarket-catalog.py'))
mapper=importlib.util.module_from_spec(mapper_spec);mapper_spec.loader.exec_module(mapper)
sem_name=mapper.sem_name

ROOT=Path('/home/tv/cardshop')
FEEDS=Path('/home/tv/.local/state/cardyssey-queue/price-feeds')
PRODUCT_URL='https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json'

def assess(names, current_id, expansions, top_limit=5):
    wanted=collections.Counter(sem_name(n) for n in names if sem_name(n))
    total=sum(wanted.values())
    if not total:return {'status':'NO_CARD_NAMES','top':[],'currentHits':0,'matchPercent':0}
    scored=[]
    for expansion_id,available in expansions.items():
        hits=sum(min(n,available.get(name,0)) for name,n in wanted.items())
        if hits:scored.append((hits,str(expansion_id)))
    scored.sort(key=lambda r:(-r[0],r[1]))
    selected=str(current_id or '')
    current_hits=next((hits for hits,exp in scored if exp==selected),0)
    top=scored[:top_limit]
    highest=scored[0][0] if scored else 0
    close=[(hits,exp) for hits,exp in scored if highest-hits<=max(1,round(total*.03)) and hits/total>=.88]
    if current_hits==0:status='SELECTED_EXPANSION_NO_NAME_OVERLAP'
    elif highest-current_hits>=max(3,round(total*.12)):status='SELECTED_EXPANSION_NEEDS_REVIEW'
    elif len(close)>1:status='AMBIGUOUS_OVERLAPPING_EXPANSIONS'
    else:status='NO_STRONG_CONFLICT_FOUND'
    return {'status':status,'currentHits':current_hits,'matchPercent':round(current_hits/total*100,1),
            'top':[{'expansionId':exp,'nameMatches':hits} for hits,exp in top],
            'competingNearEqualExpansions':len(close)}

def pg(query):
    r=subprocess.run(['docker','exec','cardyssey-db','psql','-X','-qAt','-v','ON_ERROR_STOP=1',
      '-U','cardyssey','-d','cardyssey','-c',query],capture_output=True,text=True,check=True,timeout=60)
    return json.loads(r.stdout.strip())

def run(root=ROOT,feeds=FEEDS):
    meta=json.loads((feeds/(hashlib.sha256(PRODUCT_URL.encode()).hexdigest()+'.json')).read_text())
    products=meta['products']
    expansions=collections.defaultdict(collections.Counter)
    for p in products:
        name=sem_name(p['name'])
        if name:expansions[str(p['idExpansion'])][name]+=1
    cards=pg("""SELECT COALESCE(jsonb_agg(jsonb_build_object('set',set_id,'name',name)), '[]'::jsonb)::text
      FROM catalog_cards_mirror WHERE language_code='en'""")
    chosen=pg("""SELECT COALESCE(jsonb_agg(jsonb_build_object('set',set_id,'exp',provider_expansion_id)), '[]'::jsonb)::text
      FROM cardmarket_catalog_link_candidates WHERE language_code='de' AND provider_expansion_id IS NOT NULL""")
    names=collections.defaultdict(list)
    for c in cards:names[c['set']].append(c['name'])
    selected=collections.defaultdict(collections.Counter)
    for x in chosen:selected[x['set']][str(x['exp'])]+=1
    overrides=json.loads((root/'config/cardmarket-verified-set-overrides.json').read_text())
    cases=[]
    for sid,expvotes in selected.items():
        current=expvotes.most_common(1)[0][0]
        analysis=assess(names[sid],current,expansions)
        cases.append({'setId':sid,'currentExpansion':current,'cardCount':len(names[sid]),
                      'independentlyConfirmedOverride':sid in overrides,**analysis})
    cases.sort(key=lambda x:(x['status']!='NO_STRONG_CONFLICT_FOUND',x['cardCount']),reverse=True)
    counts=collections.Counter(x['status'] for x in cases)
    report={'checkedAt':datetime.now(timezone.utc).isoformat(),'feedDate':meta.get('createdAt'),
            'setsChecked':len(cases),'statusCounts':dict(counts),'cases':cases,
            'safety':'Diagnostic only: matching card names do not prove set, collector number, language or print. Confirmed set overrides are kept; no routes or prices modified.'}
    out=root/'reports/cardmarket-set-mapping-risk-audit.json'
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},ensure_ascii=False))
    return report
if __name__=='__main__':run()
