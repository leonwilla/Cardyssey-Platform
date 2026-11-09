#!/usr/bin/env python3
"""Preflight Cardmarket filter availability BEFORE any product/browser query.

This is deliberately distinct from product identity and price confirmation.
The provider's Pokemon offer filters cover language, condition, first edition
and reverse holo; they do NOT identify every physical print like ©1999-2000.
"""
import argparse,csv,json,collections
from pathlib import Path
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
REQUIRED=('set_id','kartennummer','variante_id','drucktyp')
NON_FILTERABLE_SUBTYPES=('copyright','1999-2000','schattenlos','shadowless','kein e-reader','no-e-reader','fehler','error','missing','fehlend','blue-border')
EDITION_MARKS=('1. auflage','1st-edition','first.edition','first edition','first-edition')

def analyze(row):
    missing=[key for key in REQUIRED if not str(row.get(key) or '').strip()]
    typ=str(row.get('drucktyp') or '').strip().lower()
    if typ and typ not in ('normal','nonholo','common','reverse','holo'):
        missing.append('drucktyp_nicht_im_standardfilter')
    stamp=str(row.get('stempel') or '[]').lower()
    subtype=str(row.get('sonderdruck') or '').strip().lower()
    foil=str(row.get('foil') or '').strip().lower()
    unsupported=[]
    if any(x in subtype for x in NON_FILTERABLE_SUBTYPES):unsupported.append('sonderdruck_nicht_filterbar')
    if foil:unsupported.append('foil_muster_nicht_filterbar')
    if stamp not in ('','[]') and not any(m in stamp for m in EDITION_MARKS):unsupported.append('sonderstempel_nicht_filterbar')
    reverse='Y' if typ=='reverse' else 'N' if typ in ('normal','nonholo','common','holo') else '0'
    first='Y' if any(m in stamp for m in EDITION_MARKS) else 'N' if subtype in ('unbegrenzt','unlimited','copyright 1999-2000','1999-2000-copyright') else '0'
    return {'missing':missing,'unsupported':unsupported,'reverse':reverse,'firstEdition':first,
            'exactPrintFilterable':not(missing or unsupported)}

def summarize(language,base=BASE):
    if language not in ('de','en'):raise ValueError('invalid_language')
    p=base/f'queue-{language}.csv'
    counts=collections.Counter();examples=[];total=0
    with p.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            total+=1;r=analyze(row)
            if r['missing']:counts['missingRequired']+=1
            if r['unsupported']:counts['unfilterableSpecialPrint']+=1
            counts.update('missing:'+x for x in r['missing'])
            counts.update('unsupported:'+x for x in r['unsupported'])
            if (r['missing'] or r['unsupported']) and len(examples)<12:
                examples.append({'cardId':row['cardyssey_karte'],'variantId':row['variante_id'],
                    'setId':row.get('set_id'),'missing':r['missing'],'unsupported':r['unsupported']})
    return {'language':language,'total':total,'missingRequired':counts['missingRequired'],
            'unfilterableSpecialPrint':counts['unfilterableSpecialPrint'],
            'reasonCounts':dict(counts),'examples':examples,
            'important':'Not filterable does not mean a card is absent. A product/print comparison is necessary; no exact-print price is approved.'}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--language',choices=['de','en'],required=True);a=ap.parse_args()
    print(json.dumps(summarize(a.language),ensure_ascii=False))
