#!/usr/bin/env python3
"""Preview a user-supplied Cardmarket product link, then record a human-reviewed
exact-card identity as a durable learning example. No guess-based prices.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlsplit,parse_qs

ROOT=Path('/home/tv/cardshop')
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
STORE=Path('/home/tv/.local/state/cardyssey-queue/manual-product-previews')
PS='/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
PRODUCT_URL='https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json'
GUIDE_URL='https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json'

def valid_link(url):
    if not isinstance(url,str) or len(url)>750:return False
    try:
        p=urlsplit(url)
        if p.scheme!='https' or p.netloc!='www.cardmarket.com' or p.fragment or p.username or p.password:return False
        if re.fullmatch(r'/(de|en)/Pokemon/Products/Singles/[a-zA-Z0-9\-_.~%/]+',p.path):return True
        if p.path=='/Pokemon/Products' and re.fullmatch(r'[0-9]{3,12}',parse_qs(p.query).get('idProduct',[''])[0]):return True
    except ValueError:pass
    return False

def catalog(feed):
    cache=Path('/home/tv/.local/state/cardyssey-queue/price-feeds')/(hashlib.sha256(feed.encode()).hexdigest()+'.json')
    data=json.loads(cache.read_text(encoding='utf-8'))
    return {str(x['idProduct']):x for x in data.get('products' if feed==PRODUCT_URL else 'priceGuides',[])}

def db(sql):
    p=subprocess.run(['docker','exec','cardyssey-db','psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','cardyssey','-d','cardyssey','-c',sql],capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr[-450:])
    return p.stdout.strip()

def quote(s):return "'"+str(s).replace("'","''")+"'"

def record(lang,card,variant):
    if lang not in ('de','en') or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}',card or '') or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}',variant or ''):
        raise ValueError('invalid_card_identity')
    sql=f"""SELECT row_to_json(r)::text FROM (
     SELECT language_code,card_id,variant_id,set_id,printed_number,card_name,print_type,
     foil,subtype,stamps,provider_expansion_id,matched_set_ids,status,
     selected_product_id,reviewer_note FROM cardmarket_print_identity_review
     WHERE language_code={quote(lang)} AND card_id={quote(card)} AND variant_id={quote(variant)}
     ) r"""
    text=db(sql)
    if not text:raise ValueError('review_case_not_found')
    return json.loads(text)

def preview(data):
    lang,card,variant=data.get('language'),data.get('cardId'),data.get('variantId')
    item=record(lang,card,variant)
    url=str(data.get('url') or '').strip()
    if not valid_link(url):raise ValueError('invalid_cardmarket_url')
    cmd=[PS,'-NoProfile','-ExecutionPolicy','Bypass','-File',r'C:\Users\TV\AppData\Local\Cardyssey\CardmarketCollector\cardmarket-product-link-preview.ps1','-ProductUrl',url]
    try:proc=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=44)
    except subprocess.TimeoutExpired:raise ValueError('cardmarket_browser_timeout')
    if proc.returncode or '-File-Parameter' in proc.stderr or 'f\u00fcr den -File-Parameter' in proc.stderr:
        if 'CARDMARKET_PROVIDER_CHALLENGE' in proc.stderr:raise ValueError('cardmarket_cloudflare_blocked_try_later')
        if 'PRODUCT_ID_NOT_VISIBLE_IN_BROWSER' in proc.stderr:raise ValueError('product_id_not_visible')
        raise ValueError('cardmarket_browser_unavailable')
    try:page=json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError,json.JSONDecodeError):raise ValueError('invalid_browser_result')
    pid=str(page.get('id') or '')
    resolved=str(page.get('url') or '')
    if not re.fullmatch(r'[0-9]{3,12}',pid) or not valid_link(resolved) or '/Singles/' not in resolved:
        raise ValueError('browser_result_unverified')
    products=catalog(PRODUCT_URL)
    meta=products.get(pid)
    if meta is None:raise ValueError('product_id_missing_in_official_catalog')
    prices=catalog(GUIDE_URL).get(pid,{})
    expansion=str(meta.get('idExpansion') or '')
    expected=str(item.get('provider_expansion_id') or '')
    warnings=[]
    if expected and expansion!=expected:warnings.append('SET_ID_CONFLICT: Katalog-Kandidat und eingegebener Produktlink liegen in unterschiedlichen Cardmarket-Sets.')
    if pid not in (item.get('matched_set_ids') or []):warnings.append('PRODUCT_NOT_IN_PREVIOUS_CANDIDATES: Der frühere automatische Vorschlag war unvollständig oder falsch.')
    warnings.append('PRINT_UNVERIFIED: Der Produktfeed beweist Holo/Reverse/Edition nicht. Kartenbild und Nummer selbst vergleichen.')
    warnings.append('LANGUAGE_UNVERIFIED: Die Sprache der Cardmarket-Webseite beweist keine deutsche oder englische Kartenausgabe.')
    token=secrets.token_urlsafe(24)
    snap={'token':token,'created':datetime.now(timezone.utc).isoformat(),
          'language':lang,'cardId':card,'variantId':variant,'productId':pid,'productUrl':resolved.split('?')[0],
          'productName':str(meta.get('name') or ''),'expansionId':expansion,
          'pageHeading':str(page.get('heading') or '')[:200],
          'pageBreadcrumbs':page.get('crumbs') if isinstance(page.get('crumbs'),list) else [],
          'cardSet':item.get('set_id'),'cardNumber':item.get('printed_number'),'cardName':item.get('card_name'),
          'printType':item.get('print_type'),'warnings':warnings,'previousCandidates':item.get('matched_set_ids') or [],
          'guide':{k:prices.get(k) for k in ('avg30','avg30-holo','trend','trend-holo')},
          'languageSpecificPrice':None,'languageSpecificPriceStatus':'NOT_SCANNED'}
    STORE.mkdir(parents=True,exist_ok=True)
    target=STORE/(token+'.json');target.write_text(json.dumps(snap,ensure_ascii=False),encoding='utf-8');os.chmod(target,0o600)
    return snap

def confirm(data):
    token=str(data.get('token') or '')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{20,80}',token):raise ValueError('invalid_preview_token')
    path=STORE/(token+'.json')
    if not path.exists():raise ValueError('preview_expired_or_missing')
    snap=json.loads(path.read_text(encoding='utf-8'))
    born=datetime.fromisoformat(snap['created'])
    if datetime.now(timezone.utc)-born>timedelta(minutes=15):raise ValueError('preview_expired')
    if data.get('exactPrintConfirmed') is not True:raise ValueError('exact_print_confirmation_required')
    if any('CONFLICT' in w or 'NOT_IN_PREVIOUS' in w for w in snap['warnings']) and data.get('overrideMismatch') is not True:
        raise ValueError('acknowledge_previous_catalog_mismatch')
    lang,card,variant=snap['language'],snap['cardId'],snap['variantId']
    current=record(lang,card,variant)
    if current['status'] not in ('PENDING_REVIEW','DEFERRED'):
        raise ValueError('review_case_already_decided')
    pid,url=snap['productId'],snap['productUrl']
    original=','.join(str(x) for x in current.get('matched_set_ids') or [])
    # One transaction preserves a complete audit of the input and the old candidates.
    sql=f"""BEGIN;
CREATE TABLE IF NOT EXISTS cardmarket_manual_identity_examples (
  id BIGSERIAL PRIMARY KEY,language_code TEXT NOT NULL,card_id TEXT NOT NULL,
  variant_id TEXT NOT NULL,card_set TEXT,card_number TEXT,card_name TEXT,
  print_type TEXT,product_id TEXT NOT NULL,product_url TEXT NOT NULL,
  product_expansion_id TEXT,product_name TEXT,previous_candidate_ids TEXT,
  correction_reason TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
WITH reviewed AS (
 UPDATE cardmarket_print_identity_review SET status='CONFIRMED_PRINT',selected_product_id={quote(pid)},
 reviewer_note={quote('Manual link correction: '+str(data.get('note') or '')[:300])},reviewed_at=NOW(),
 candidate_ids=CASE WHEN candidate_ids ? {quote(pid)} THEN candidate_ids ELSE candidate_ids || to_jsonb({quote(pid)}::text) END,
 matched_set_ids=CASE WHEN matched_set_ids ? {quote(pid)} THEN matched_set_ids ELSE matched_set_ids || to_jsonb({quote(pid)}::text) END,
 classification='HUMAN_CONFIRMED_URL_OVERRIDE'
 WHERE language_code={quote(lang)} AND card_id={quote(card)} AND variant_id={quote(variant)}
 AND status IN ('PENDING_REVIEW','DEFERRED') RETURNING card_id
), mapped AS (
 INSERT INTO price_source_routing(language_code,card_id,variant_id,primary_provider,provider_product_id,
 provider_product_url,source_evidence,verification_state,fallback_provider,refresh_days,next_attempt_at)
 SELECT {quote(lang)},{quote(card)},{quote(variant)},'CARDMARKET',{quote(pid)},{quote(url)},
 'Human confirmed exact set, number, language, edition, foil and stamp; supplied URL','VERIFIED_PRODUCT_ID','TCGDEX',7,NOW()
 FROM reviewed
 ON CONFLICT(language_code,card_id,variant_id) DO UPDATE SET
 primary_provider='CARDMARKET',provider_product_id=EXCLUDED.provider_product_id,
 provider_product_url=EXCLUDED.provider_product_url,source_evidence=EXCLUDED.source_evidence,
 verification_state='VERIFIED_PRODUCT_ID',next_attempt_at=NOW(),updated_at=NOW()
 WHERE price_source_routing.verification_state<>'VERIFIED_PRODUCT_ID'
 OR (price_source_routing.primary_provider='CARDMARKET' AND price_source_routing.provider_product_id=EXCLUDED.provider_product_id)
 RETURNING card_id
), trained AS (
 INSERT INTO cardmarket_manual_identity_examples(language_code,card_id,variant_id,card_set,card_number,card_name,
 print_type,product_id,product_url,product_expansion_id,product_name,previous_candidate_ids,correction_reason)
 SELECT {quote(lang)},{quote(card)},{quote(variant)},{quote(snap['cardSet'])},{quote(snap['cardNumber'])},
 {quote(snap['cardName'])},{quote(snap['printType'])},{quote(pid)},{quote(url)},
 {quote(snap['expansionId'])},{quote(snap['productName'])},{quote(original)},
 {quote(' | '.join(snap['warnings']))} FROM mapped RETURNING id
)
SELECT json_build_object('reviewed',(SELECT count(*) FROM reviewed),'mapped',(SELECT count(*) FROM mapped),
 'exampleSaved',(SELECT count(*) FROM trained))::text;
DO $block$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM price_source_routing WHERE language_code={quote(lang)}
  AND card_id={quote(card)} AND variant_id={quote(variant)}
  AND primary_provider='CARDMARKET' AND provider_product_id={quote(pid)}
  AND verification_state='VERIFIED_PRODUCT_ID') THEN
 RAISE EXCEPTION 'existing_verified_mapping_conflict'; END IF;
END $block$;
COMMIT;"""
    output=db(sql)
    result=json.loads(next((x for x in output.splitlines() if x.startswith('{')), '{}'))
    if result.get('mapped')!=1:raise ValueError('existing_verified_mapping_conflict')
    # Queue uses the exact same persisted ID and URL on the next scan.
    from importlib.util import spec_from_file_location,module_from_spec
    src=ROOT/'scripts/cardmarket-print-review-admin.py'
    spec=spec_from_file_location('review',src);m=module_from_spec(spec);spec.loader.exec_module(m)
    queueUpdated=m.sync_queue_identity(lang,card,variant,pid,product_url=url)
    path.unlink(missing_ok=True)
    return {'ok':True,'productId':pid,'productUrl':url,'queueUpdated':queueUpdated,
        'exampleSaved':result.get('exampleSaved')==1,
        'priceStatus':'PENDING_VERIFIED_LANGUAGE_AND_PRINT_FILTER_SCAN'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--action',choices=['preview','confirm'],required=True);a=ap.parse_args()
    try:
        req=json.load(sys.stdin)
        if not isinstance(req,dict):raise ValueError('invalid_payload')
        print(json.dumps(preview(req) if a.action=='preview' else confirm(req),ensure_ascii=False))
    except (ValueError,TypeError,RuntimeError,OSError) as e:
        print(json.dumps({'error':str(e)[:250]},ensure_ascii=False));sys.exit(2)
if __name__=='__main__':main()
