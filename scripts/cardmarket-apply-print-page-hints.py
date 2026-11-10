#!/usr/bin/env python3
"""Attach verified *card page* leads; never claim exact print/offer price.

Validated against expected card/set/collector slug. A link to a shared
product page is NOT evidence of a specific stamp, foil, edition or language.
"""
import argparse,csv,json,os,tempfile
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path('/home/tv/cardshop')
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')

def apply(language,base=BASE,root=ROOT):
    if language not in ('de','en'):raise ValueError('invalid language')
    rules=json.loads((root/'config/cardmarket-known-print-page-hints.json').read_text())
    path=base/f'queue-{language}.csv'
    with path.open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f);fields=list(r.fieldnames or []);rows=list(r)
    for col in ('reference_product_url','reference_print_verified','reference_evidence','reference_standard_filter_supported','catalog_singleton_id','catalog_expansion_id'):
        if col not in fields:fields.append(col)
    counts={'language':language,'rows':len(rows),'knownPages':0,'printConfirmedByReference':0,'standardOfferFilterCandidates':0}
    seen=set()
    for row in rows:
        row['reference_product_url']='';row['reference_print_verified']='NO';row['reference_evidence']='';row['reference_standard_filter_supported']='NO'
        card=row['cardyssey_karte'];var=row['variante_id']
        if card not in rules:continue
        rule=rules[card];choice=rule['variants'].get(var)
        if choice is None:continue
        assert card not in ('',None) and row.get('set_id')==card.rsplit('-',1)[0],(card,row.get('set_id'))
        assert choice['slug'].endswith('-'+rule['collectorSuffix']),(card,choice)
        assert choice.get('printVerified') is False,'Hint cannot claim exact print proof'
        assert all('/' not in choice[k] for k in ('slug',)),choice
        url='https://www.cardmarket.com/'+language+'/Pokemon/Products/Singles/'+rule['setSlug']+'/'+choice['slug']
        assert urlparse(url).hostname=='www.cardmarket.com'
        row['reference_product_url']=url
        row['reference_print_verified']='NO'
        row['reference_evidence']=choice['evidence']
        standard=choice.get('standardFilterProductId')
        if standard:
            assert str(standard).isdigit() and str(choice.get('standardFilterExpansionId') or '').isdigit()
            assert row['drucktyp'].strip().lower() in ('normal','reverse'),row
            assert str(row.get('stempel') or '') in ('','[]') and not str(row.get('foil') or '') and not str(row.get('sonderdruck') or ''),'special print must not become standard'
            assert choice['slug'].startswith('Sprigatito-V1-') and card=='sv01-013','standard evidence must be inspected'
            # Official set-repair should have populated the complete list.
            # In dry-runs/temporary queues, this independently browser-verified
            # product is still safe as a *candidate*; never publish it as a
            # reviewed physical print or price just because the list was empty.
            if str(standard) not in str(row.get('cardmarket_ids') or '').split(','):
                current=[x for x in str(row.get('cardmarket_ids') or '').split(',') if x.isdigit()]
                row['cardmarket_ids']=','.join(sorted(set(current+[str(standard)]),key=int))
            # This is a *standard offer-filter candidate*, not human confirmation.
            # Preserve current human-confirmed IDs and prices in all cases.
            if row.get('routing_state')!='VERIFIED_PRODUCT_ID':
                row['catalog_singleton_id']=str(standard)
                row['catalog_expansion_id']=str(choice['standardFilterExpansionId'])
                row['reference_standard_filter_supported']='YES'
                counts['standardOfferFilterCandidates']+=1
        key=(card,var)
        assert key not in seen,'duplicate reference'
        seen.add(key);counts['knownPages']+=1
    fd,tmp=tempfile.mkstemp(prefix=f'queue-{language}-refs-',suffix='.csv.tmp',dir=base)
    try:
        with os.fdopen(fd,'w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return counts
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--language',required=True,choices=('de','en'));a=parser.parse_args()
    print(json.dumps(apply(a.language)))
