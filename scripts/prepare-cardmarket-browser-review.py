#!/usr/bin/env python3
"""Prepare a review-only queue from safe Cardmarket catalog candidates; no login or scraping."""
import argparse,csv,json
from collections import Counter
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--input',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args()
items=json.loads(args.input.read_text(encoding='utf-8'))['unresolved']
args.output_dir.mkdir(parents=True,exist_ok=True)
rows=[]
for x in items:
    candidates=x.get('products') or []
    variant=x.get('variant') or {}
    flags=x.get('unverified_identity_fields') or []
    # This is a review order, not proof of correctness.
    priority='A' if x.get('set_verified') and len(candidates)==1 else 'B' if x.get('set_verified') and candidates else 'C' if candidates else 'D'
    if variant.get('subtype') or variant.get('foil') or variant.get('stamps'):
        priority= 'B' if priority=='A' else priority
    rows.append({'prioritaet':priority,'status':'ZU_PRUEFEN','set_id':x.get('set_code') or '',
      'kartennummer':x.get('number') or '','kartenname_suche':x.get('english_name') or '',
      'cardyssey_karte':x.get('card_id') or '', 'variante_id':x.get('variant_id') or '',
      'drucktyp':variant.get('type') or '', 'sonderdruck':variant.get('subtype') or '',
      'foil':variant.get('foil') or '', 'stempel':','.join(variant.get('stamps') or []),
      'produktkandidaten':len(candidates),'cardmarket_ids':','.join(str(c.get('id') or '') for c in candidates),
      'cardmarket_namen':' | '.join(str(c.get('name') or '') for c in candidates),
      'offen_zu_pruefen':','.join(flags),'suche':x.get('search_query') or '',
      'manuell_bestaetigte_id':'','manuell_bestaetigte_edition':'','manuell_bestaetigte_sprache':'','notizen':''})
rows.sort(key=lambda x:(x['prioritaet'],x['set_id'],x['cardyssey_karte'],x['variante_id']))
path=args.output_dir/'de_offene_cardmarket_varianten.csv'
with path.open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
summary={'total':len(rows),'with_product_candidates':sum(bool(x['produktkandidaten']) for x in rows),
 'priorities':dict(Counter(r['prioritaet'] for r in rows)),'first_examples':[{k:r[k] for k in ('set_id','cardyssey_karte','sonderdruck','cardmarket_ids')} for r in rows[:5]]}
(args.output_dir/'status.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
print(path)
