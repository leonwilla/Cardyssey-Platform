#!/usr/bin/env python3
"""Persist confirmed print decisions + unverified version-family candidates.

Reads only local human reviews and archived browser observations. Never maps
V1/V2 by order or price. Never changes price_source_routing/tcg_price_cache.
Exports a tiny verified-only file consumed by the Cardmarket browser collector.
"""
import argparse,json,os,re,subprocess,tempfile
from pathlib import Path
ROOT=Path('/home/tv/cardshop')
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
EVIDENCE=ROOT/'config/cardmarket-version-family-evidence.json'
def sql_quote(s):return "'"+str(s).replace("'","''")+"'"
def run(sql):
    p=subprocess.run(['docker','exec','-i','cardyssey-db','psql','-X','-qAt',
      '-v','ON_ERROR_STOP=1','-U','cardyssey','-d','cardyssey'],
      input=sql,text=True,capture_output=True,timeout=45)
    if p.returncode:raise RuntimeError(p.stderr[-700:])
    return p.stdout.strip()
def pending_queries(data):
    statements=[]
    for cid,item in data.items():
        if (item.get('cardId')!=cid or item.get('status')!='VERSION_FAMILY_PRINT_UNVERIFIED'
              or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,120}',cid)):continue
        rows=item.get('sameSetCardNumberCandidates') or []
        for v in rows:
            pid=str(v.get('productId') or '')
            url=str(v.get('productUrl') or '')
            if not v.get('productIdChecked') or not re.fullmatch(r'[0-9]{4,12}',pid):continue
            if not url.startswith('https://www.cardmarket.com/') or '/Pokemon/Products/Singles/' not in url:continue
            setslug=v.get('setSlug') or ''
            if not re.fullmatch(r'[A-Za-z0-9-]{2,90}',setslug):continue
            # An exact observed family is evidence for a page candidate,
            # NOT evidence that e.g. V1 is Pokéball or V2 Master Ball.
            evid=json.dumps({'version':v.get('version'),'pageUrl':url,
                 'observedFrom':item.get('versionPageUrl'),
                 'exactPrintVerified':False,'priceVerified':False},ensure_ascii=False)
            statements.append(f"""INSERT INTO cardmarket_variant_mappings
 (language_code,card_id,variant_id,product_id,print_type,set_slug,product_url,
  is_reverse_holo,required_comment_pattern,mapping_status,confidence,evidence_type,evidence)
 SELECT r.language_code,r.card_id,r.variant_id,{sql_quote(pid)},
  'unknown',{sql_quote(setslug)},{sql_quote(url)},NULL,NULL,
  'PENDING_REVIEW','LOW','BROWSER_VERSION_FAMILY',{sql_quote(evid)}::jsonb
 FROM cardmarket_print_identity_review r
 WHERE r.card_id={sql_quote(cid)} AND r.language_code IN ('de','en')
 ON CONFLICT (language_code,card_id,variant_id,product_id) DO NOTHING;""")
    return statements

HUMAN_SYNC="""
INSERT INTO cardmarket_variant_mappings
(language_code,card_id,variant_id,product_id,print_type,set_slug,product_url,
 is_reverse_holo,required_comment_pattern,mapping_status,confidence,
 evidence_type,evidence,confirmed_by,verified_at)
SELECT r.language_code,r.card_id,r.variant_id,r.selected_product_id,
 CASE
 WHEN lower(COALESCE(r.foil,'')) LIKE '%meisterball%' OR lower(COALESCE(r.foil,'')) LIKE '%masterball%' THEN 'masterball'
 WHEN lower(COALESCE(r.foil,'')) LIKE '%pok%ball%' THEN 'pokeball'
 WHEN COALESCE(r.stamps,'[]') NOT IN ('','[]') THEN 'stamp'
 WHEN lower(COALESCE(r.print_type,'')) LIKE '%reverse%' THEN 'reverse'
 WHEN lower(COALESCE(r.print_type,''))='normal' THEN 'normal'
 WHEN lower(COALESCE(r.print_type,'')) LIKE '%holo%' THEN 'holo'
 ELSE 'unknown' END,
 NULL,
 CASE WHEN route.provider_product_url LIKE 'https://www.cardmarket.com/%'
  THEN route.provider_product_url ELSE NULL END,
 CASE WHEN lower(COALESCE(r.print_type,'')) LIKE '%reverse%' THEN TRUE
      WHEN lower(COALESCE(r.print_type,''))='normal' THEN FALSE ELSE NULL END,
 NULL,
 'HUMAN_CONFIRMED','HIGH','CARDYSSEY_HUMAN_REVIEW',
 jsonb_build_object('reviewedAt',r.reviewed_at,'reviewerNote',r.reviewer_note,
                    'source','cardmarket_print_identity_review'),
 'cardyssey-admin',COALESCE(r.reviewed_at,NOW())
FROM cardmarket_print_identity_review r
LEFT JOIN price_source_routing route
 ON route.language_code=r.language_code AND route.card_id=r.card_id
 AND route.variant_id=r.variant_id AND route.primary_provider='CARDMARKET'
 AND route.provider_product_id=r.selected_product_id
WHERE r.status='CONFIRMED_PRINT' AND r.selected_product_id ~ '^[0-9]{4,12}$'
ON CONFLICT (language_code,card_id,variant_id,product_id) DO UPDATE SET
 mapping_status='HUMAN_CONFIRMED', confidence='HIGH',
 print_type=EXCLUDED.print_type,
 is_reverse_holo=EXCLUDED.is_reverse_holo,
 product_url=COALESCE(EXCLUDED.product_url,cardmarket_variant_mappings.product_url),
 evidence_type='CARDYSSEY_HUMAN_REVIEW', evidence=EXCLUDED.evidence,
 confirmed_by=EXCLUDED.confirmed_by, verified_at=EXCLUDED.verified_at,
 updated_at=NOW();
"""
def sync(apply=False,base=BASE,evidence_file=EVIDENCE):
    families=json.loads(evidence_file.read_text(encoding='utf-8'))
    pending=pending_queries(families)
    if apply:
        # Revoke an identity if the earlier manual review was undone.
        revoke="""UPDATE cardmarket_variant_mappings m
           SET mapping_status='PENDING_REVIEW',confidence='LOW',
               confirmed_by=NULL,verified_at=NULL,
               evidence_type='REVIEW_UNDONE',updated_at=NOW()
           WHERE mapping_status='HUMAN_CONFIRMED'
             AND NOT EXISTS (SELECT 1 FROM cardmarket_print_identity_review r
                 WHERE r.language_code=m.language_code AND r.card_id=m.card_id
                   AND r.variant_id=m.variant_id AND r.status='CONFIRMED_PRINT'
                   AND r.selected_product_id=m.product_id);"""
        run("BEGIN;\n"+revoke+"\n"+"\n".join(pending)+"\n"+HUMAN_SYNC+"\nCOMMIT;")
    data=json.loads(run("""SELECT json_build_object(
      'confirmedCount',(SELECT count(*) FROM cardmarket_variant_mappings WHERE mapping_status='HUMAN_CONFIRMED'),
      'candidateCount',(SELECT count(*) FROM cardmarket_variant_mappings WHERE mapping_status='PENDING_REVIEW'),
      'confirmed',COALESCE((SELECT json_agg(z) FROM
        (SELECT language_code,card_id,variant_id,product_id,print_type,
          product_url,set_slug,is_reverse_holo,mapping_status
         FROM cardmarket_variant_mappings WHERE mapping_status='HUMAN_CONFIRMED'
         ORDER BY language_code,card_id,variant_id) z),'[]'::json))::text"""))
    output={'schema':1,'source':'CARDYSSEY_HUMAN_CONFIRMED_PRINT_ONLY',
       'confirmedMappings':data.get('confirmed') or [],
       'confirmedCount':data['confirmedCount'],'pendingCandidates':data['candidateCount'],
       'familyCandidateStatements':len(pending),'pricesUpdated':0}
    if apply:
        base.mkdir(parents=True,exist_ok=True)
        dest=base/'cardmarket-verified-print-mapping-cache.json'
        fd,tmp=tempfile.mkstemp(prefix='cm-confirmed-',suffix='.tmp',dir=base)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(output,f,ensure_ascii=False,separators=(',',':'))
            os.replace(tmp,dest)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    return {'mode':'APPLIED' if apply else 'DRY_RUN',
      'confirmedCount':output['confirmedCount'],
      'pendingCandidates':output['pendingCandidates'],
      'familyCandidateStatements':len(pending),
      'exportedVerifiedOnly':len(output['confirmedMappings']),
      'pricesUpdated':0}
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    print(json.dumps(sync(apply=args.apply),ensure_ascii=False))
