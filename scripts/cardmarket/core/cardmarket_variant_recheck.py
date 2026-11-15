#!/usr/bin/env python3
"""Rescan the local DE/EN Cardmarket catalog and browser evidence safely.

This does NOT infer language availability from website locale or a product ID,
NOR guess that V2 is always Holo. No price, review decision or routing writes.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from cardmarket_print_routes import SUBSET_EVIDENCE, VINTAGE_EVIDENCE, read_list

ROOT=Path('/home/tv/cardshop')
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
FEEDS=Path('/home/tv/.local/state/cardyssey-queue/price-feeds')
URL='https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json'
URL_VERSION=re.compile(r'(?i)(?:^|[-/])V([1-9][0-9]?)(?=[-/]|$)')
COMPLETED={'COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED','FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE','NO_CONFIRMED_FILTERED_OFFERS','FILTER_UNAVAILABLE','FILTER_UNVERIFIED_EMPTY','MAPPED_NO_PRICE_REQUIRED','FILTER_NOT_APPLIED'}

def read_latest(lang,base=BASE):
    path=base/f'browser-observations-{lang}.jsonl'
    result={}
    if path.exists():
        for line in path.open(encoding='utf-8-sig'):
            try:
                x=json.loads(line)
                if x.get('card_id') and x.get('variant_id'):
                    result[(x['card_id'],x['variant_id'])]=x
            except (ValueError,TypeError):pass
    return result

def candidate_audit(row,products,obs,supplemental=None,user_reference_url=None):
    ids=[v for v in row.get('matched_set_ids','').split(',') if v]
    product_records=[products.get(i) for i in ids]
    evidence=(obs or {}).get('url') or ''
    version=URL_VERSION.search(evidence.split('?')[0])
    has_filtered=bool(obs and obs.get('identity_confirmed') is True and obs.get('status') in COMPLETED)
    lang_proof=bool(has_filtered and int(obs.get('verified_lang_nm_offers') or 0)>0)
    evidence_pid=str(obs.get('product_id') or '') if obs else ''
    # Version in a verified URL is evidence for the OBSERVED product only,
    # not for every similarly named product in the source catalog.
    confirmed_url=bool(version and has_filtered and evidence_pid in ids)
    version_pages=(supplemental or {}).get('versionPages') or []
    independent_versions={x.get('version') for x in version_pages if
        isinstance(x,dict) and str(x.get('url','')).startswith('https://www.cardmarket.com/')}
    user_version_compare=len(independent_versions)>1
    # A user-supplied URL is a useful lookup hint, not a reason to require
    # manual set assignment. One catalog product in the independently
    # verified set must first go through automatic print/language checking.
    classification=row.get('classification','')
    if classification in (SUBSET_EVIDENCE,VINTAGE_EVIDENCE):
        category='MANUAL_COMPARISON_READY'
        reason='Kartenreferenz vorhanden. Druckmerkmal und passendes Angebot manuell prüfen.'
    elif 'CARD_IN_VERIFIED_SET_PRINT_NOT_IDENTIFIED' in classification and ids:
        category='AUTO_PRINT_VERIFICATION'
        reason='Kartennummer und Cardmarket-Set sind bekannt; Produktkandidaten sind noch keiner physischen Druckvariante zugewiesen.'
    elif not ids or 'SET_NOT_VERIFIED' in row.get('classification','') or 'NO_MATCH' in row.get('classification','') or 'INFERRED_SET' in row.get('classification',''):
        category='AUTO_CATALOG_RECHECK'
        reason='Set oder Produktidentität zunächst durch Automatik klären'
    elif len(ids)>1:
        category='MANUAL_COMPARISON_READY' if (confirmed_url or user_version_compare) else 'AUTO_VERSION_DISCOVERY'
        reason=('Version auf einer bestätigten Produktseite gefunden; andere Kandidaten müssen noch verglichen werden' if confirmed_url else
                'V1/V2-Bilder wurden bereitgestellt, die numerischen Produkt-IDs sind aber noch keiner Version verlässlich zugeordnet' if user_version_compare else
                'Mehrere Produkte: erst V1/V2, Bilder und Druck der Kandidaten nachweisen')
    elif obs and obs.get('status')=='PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED':
        category='AUTO_PRINT_VERIFICATION'
        reason='Produkt ist im bestätigten Set mit passender Kartennummer gefunden; nur die konkrete Druck-/Editionsvariante ist noch offen.'
    elif has_filtered and lang_proof:
        category='AUTO_PRINT_VERIFICATION'
        reason='Produktseite und Angebote in dieser Sprache gefunden; Druck/Edition noch zu verifizieren'
    else:
        category='AUTO_LANGUAGE_AND_PRINT_RECHECK'
        reason='Sprache/Edition/Druck noch nicht unabhängig nachgewiesen'
    meta_ids={str(p.get('idMetacard')) for p in product_records if p and p.get('idMetacard')}
    return {'category':category,'reason':reason,'versionObserved':'V'+version.group(1) if confirmed_url else None,
            'versionProductId':evidence_pid if confirmed_url else None,
            'languageOffersObserved':lang_proof,
            'languageAvailability':'OFFERS_OBSERVED' if lang_proof else 'UNKNOWN_NOT_PROVEN_ABSENT',
            'sameMetacard':len(ids)>1 and len(meta_ids)==1,
            'printVerified':False,'priceApproved':False,
            'versionPages':version_pages if user_version_compare else [],
            'referencePageUrl':row.get('reference_product_url') or '',
            'referenceCandidateUrls':read_list(row.get('reference_candidate_urls')),
            'lastScanStatus':obs.get('status') if obs else 'NOT_SCANNED'}

def run(lang,root=ROOT,base=BASE,feeds=FEEDS):
    meta=json.loads((feeds/(hashlib.sha256(URL.encode()).hexdigest()+'.json')).read_text())
    products={str(x['idProduct']):x for x in meta['products']}
    latest=read_latest(lang,base)
    evidence_path=root/'config/cardmarket-page-version-evidence.json'
    supplied=json.loads(evidence_path.read_text(encoding='utf-8')) if evidence_path.exists() else {}
    user_links_path=root/'config/cardmarket-user-reference-links.json'
    user_links=json.loads(user_links_path.read_text(encoding='utf-8')) if user_links_path.exists() else {}
    src=root/f'reports/cardmarket-identity-worklist-{lang}.csv'
    out=root/f'reports/cardmarket-variant-recheck-{lang}.json'
    counts=Counter(); cases={}; seen=0
    with src.open(newline='',encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            seen+=1
            key=(row['card_id'],row['variant_id'])
            info=candidate_audit(row,products,latest.get(key),supplied.get(lang+'|'+row['card_id']),user_links.get(row['card_id']))
            counts[info['category']]+=1
            if info['versionObserved']:counts['observed_version_url']+=1
            if info['languageOffersObserved']:counts['observed_language_offers']+=1
            # Restrict report to candidates requiring follow-up; metadata is
            # bounded per-card, never store account cookies or offer photos.
            if row.get('classification')!='ONE_PRODUCT_IN_VERIFIED_SET' or user_links.get(row['card_id']):
                cases['|'.join(key)]=info
    result={'language':lang,'createdAt':datetime.now(timezone.utc).isoformat(),
            'sourceCatalogCreatedAt':meta.get('createdAt'),
            'scannedWorklistRows':seen,'browserRecords':len(latest),
            'counts':dict(counts),'cases':cases,
            'note':'Only independently verified version URL is retained. No V1=normal / V2=holo assumption. Missing offers never proves nonexistence.'}
    tmp=out.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    tmp.replace(out)
    return {k:v for k,v in result.items() if k!='cases'}

if __name__=='__main__':
    for language in ('de','en'):
        print(json.dumps(run(language),ensure_ascii=False))
