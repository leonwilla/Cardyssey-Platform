#!/usr/bin/env python3
"""Admin-only scan failures and CSV exports from scanner JSONL logs.
The worklist remains distinct from catalog print review. No guesses or writes.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse,csv,json,importlib.util,subprocess
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from cardmarket_print_routes import SUBSET_EVIDENCE, VINTAGE_EVIDENCE, reference_urls
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
spec=importlib.util.spec_from_file_location('filter_readiness',Path(__file__).resolve().parents[0].parent/'core'/'cardmarket-filter-readiness.py')
filter_readiness=importlib.util.module_from_spec(spec);spec.loader.exec_module(filter_readiness)
SUCCESS={'MAPPED_NO_PRICE_REQUIRED','COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED','COMPLETE_FILTERED_ASKING_MEDIAN','SOURCE_ONLY','SUCCESS','SET_MAPPING_PENDING'}
PRICE_LIMIT_STATUSES={'FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE','NO_CONFIRMED_FILTERED_OFFERS','FILTER_UNAVAILABLE','FILTER_UNVERIFIED_EMPTY','FILTER_NOT_APPLIED'}
TECHNICAL={'BLOCKED','LOGIN_REQUIRED','ERROR','PROVIDER_ERROR','PROVIDER_TIMEOUT','CONNECTION_LOST','FILTER_UNAVAILABLE','FILTER_UNVERIFIED_EMPTY','FILTER_NOT_APPLIED','NO_CONFIRMED_FILTERED_OFFERS','FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE'}
CANDIDATE_URL_LIMIT = 5
PRINT_PAGE_REVIEW_STATUSES = {'MULTIPLE_SEARCH_HITS','NO_EXACT_NUMBER_SEARCH_HIT',
    'PRODUCT_ID_NOT_VERIFIED_FOR_CARD','PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED','PRODUCT_SET_SLUG_MISMATCH'}
CSV_COLUMNS = (
    ('Sprache', 'language'),
    ('Prüfbereich', 'type'),
    ('Statuscode', 'status'),
    ('Fehlerdetail', 'detail'),
    ('Set-ID', 'setId'),
    ('Kartennummer', 'cardNumber'),
    ('Kartenname', 'name'),
    ('Karten-ID', 'cardId'),
    ('Varianten-ID', 'variantId'),
    ('Drucktyp', 'printType'),
    ('Sonderdruck', 'specialPrint'),
    ('Stempel', 'printStamp'),
    ('Foil', 'printFoil'),
    ('Produkt-ID', 'productId'),
    ('Produkt-URL', 'productUrl'),
    ('Referenz-URL', 'referenceUrl'),
    ('Suchanfrage', 'searchQuery'),
    ('Set-/Nummern-Scoring', 'scoreMatchState'),
    ('Anzahl Suchkandidaten', 'scoreCandidateCount'),
    ('Nur Seitenkandidat', 'scorePageCandidateOnly'),
    ('Fehlende Pflichtangaben', 'missingFields'),
    ('Nicht filterbare Druckmerkmale', 'unfilterablePrintFeatures'),
    ('Angebotsfilter', 'filterMode'),
    ('Zuletzt geprüft', 'seenAt'),
)

def classify(status,entry=None,queue=None,references=()):
    if status in PRINT_PAGE_REVIEW_STATUSES and references:
        return 'DRUCKPRUEFUNG'
    if (status == 'PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED' and entry
            and entry.get('reference_page_evidence') in (SUBSET_EVIDENCE,VINTAGE_EVIDENCE)
            and entry.get('exact_print_filter_supported') is False):
        return 'DRUCKPRUEFUNG'
    if status=='PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED' and entry and queue:
        if (entry.get('catalog_direct_id_verified') is True and
            str(entry.get('product_id') or '')==str(queue.get('catalog_singleton_id') or '') and
            str(queue.get('catalog_expansion_id') or '').isdigit()):
            # Only unfilterable special prints need a human. A standard
            # normal/holo/reverse can be handled by the existing filtered
            # price pipeline; identity evidence by itself is never a price.
            attrs=filter_readiness.analyze(queue)
            if attrs['unsupported'] or attrs['missing'] or str(queue.get('sonderdruck') or '').strip():
                return 'DRUCKPRUEFUNG'
            return 'PREISPRUEFUNG'
    # A separately known and set-guarded card page makes same-name search
    # failures redundant: the only missing information is the physical stamp
    # or foil. Keep these in a DISTINCT print-review tab; do not falsely
    # suggest the user must identify which Pokémon or set it is again.
    if queue and status in ('MULTIPLE_SEARCH_HITS','NO_EXACT_NUMBER_SEARCH_HIT','PRODUCT_ID_NOT_VERIFIED_FOR_CARD'):
        ref=str(queue.get('reference_product_url') or '')
        stamp=str(queue.get('stempel') or '[]')
        foil=str(queue.get('foil') or '')
        sid=str(queue.get('set_id') or '')
        guard_path=Path('/home/tv/cardshop/config/cardmarket-set-url-guards.json')
        try:guards=json.loads(guard_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):guards={}
        try:
            parsed=urlsplit(ref)
            approved=parsed.scheme=='https' and parsed.hostname=='www.cardmarket.com' and f'/Pokemon/Products/Singles/{guards.get(sid,"__UNKNOWN__")}/' in parsed.path
        except ValueError:approved=False
        if approved and (stamp not in ('','[]') or foil):return 'DRUCKPRUEFUNG'
    # Card+product match is established. Incomplete price pagination does NOT
    # create an identity/print decision for the founder. Scope this rule to
    # 30th sets until other releases have been independently audited.
    if status in PRICE_LIMIT_STATUSES and entry and queue and str(queue.get('set_id') or '').startswith('30th'):
        pid=str(entry.get('product_id') or '')
        candidates={x.strip() for x in str(queue.get('cardmarket_ids') or '').split(',') if x.strip()}
        known_route=str(queue.get('known_url') or '')
        if entry.get('identity_confirmed') is True and pid.isdigit() and pid in candidates and (known_route or queue.get('routing_state')=='VERIFIED_PRODUCT_ID'):
            return 'PREISPRUEFUNG'
        if entry.get('identity_confirmed') is True and pid.isdigit() and candidates and pid not in candidates:
            return 'ZUORDNUNG'

    if status=='MISSING_REQUIRED_SCAN_FIELDS':return 'DATEN_FEHLEN'
    if status in SUCCESS:return None
    if status in TECHNICAL or status.startswith('DEFERRED') or status.startswith('FILTER_') or status.startswith('NO_CONFIRMED'):return 'TECHNISCH'
    if status.startswith('COMPLETE_') or status in ('STARTED','RUNNING'):return None
    return 'ZUORDNUNG'

def reviewed_decisions(language):
    """Current decisions for exact (card, physical variant), DB read only."""
    if language not in ('de','en'):raise ValueError('invalid_language')
    sql=("SELECT card_id,variant_id,status,reviewed_at::text,COALESCE(selected_product_id,'') "
         "FROM cardmarket_print_identity_review WHERE language_code='"+language+
         "' AND status IN ('CONFIRMED_PRINT','NO_MATCH','DEFERRED') AND reviewed_at IS NOT NULL")
    try:
        p=subprocess.run(['docker','exec','cardyssey-db','psql','-X','-qAt','-v','ON_ERROR_STOP=1','-F','|','-U','cardyssey','-d','cardyssey','-c',sql],
                         capture_output=True,text=True,check=True,timeout=12)
    except (subprocess.SubprocessError,OSError):return {}
    out={}
    for line in p.stdout.splitlines():
        fields=line.split('|')
        if len(fields)==5:out[(fields[0],fields[1])]={'status':fields[2],'reviewedAt':fields[3],'selectedProductId':fields[4]}
    return out

def resolved_after_scan(observation,decision):
    if not decision or decision.get('status') not in ('CONFIRMED_PRINT','NO_MATCH','DEFERRED'):return False
    # Once the exact physical print has been human-confirmed, a subsequent
    # name-only/no-result browser failure does not erase that confirmation.
    # A NEW positive contradictory product ID is still surfaced for debugging.
    if decision['status']=='CONFIRMED_PRINT':
        product=str(observation.get('product_id') or '')
        chosen=str(decision.get('selectedProductId') or '')
        if chosen and (not product or product==chosen):return True
    try:
        reviewed=datetime.fromisoformat(str(decision['reviewedAt']).replace('Z','+00:00'))
        seen=datetime.fromisoformat(str(observation.get('seen_at') or '').replace('Z','+00:00'))
        if reviewed.tzinfo is None:reviewed=reviewed.replace(tzinfo=timezone.utc)
        if seen.tzinfo is None:seen=seen.replace(tzinfo=timezone.utc)
        return reviewed>=seen
    except (TypeError,ValueError):return False

def list_failures(base=BASE,language='de',page=0,search='',scope='current',kind='karten',decisions=None,*,for_export=False):
    if language not in ('de','en'):raise ValueError('invalid_language')
    if scope not in ('current','all'):raise ValueError('invalid_scope')
    if kind not in ('karten','preise','technik','drucke','alle'):raise ValueError('invalid_kind')
    if not 0<=page<=2000:raise ValueError('invalid_page')
    epoch=None
    ep=base/'full-rescan-epoch.json'
    if ep.exists():
        try:epoch=datetime.fromisoformat(json.loads(ep.read_text(encoding='utf-8-sig'))['requestedAt'].replace('Z','+00:00'))
        except (ValueError,KeyError):pass
    rows={}
    p=base/f'browser-observations-{language}.jsonl'
    if p.exists():
        with p.open(encoding='utf-8-sig') as f:
            for line in f:
                try:entry=json.loads(line)
                except (TypeError,ValueError):continue
                card=str(entry.get('card_id') or '');var=str(entry.get('variant_id') or '')
                if not card or not var:continue
                if scope=='current' and epoch:
                    try:
                        seen=datetime.fromisoformat(str(entry.get('seen_at','')).replace('Z','+00:00'))
                        if seen<epoch:continue
                    except ValueError:continue
                rows[(card,var)]=entry
    queue={}
    with (base/f'queue-{language}.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):queue[(r.get('cardyssey_karte'),r.get('variante_id'))]=r
    if decisions is None:decisions=reviewed_decisions(language) if base==BASE else {}
    output=[]
    for key,entry in rows.items():
        if resolved_after_scan(entry,decisions.get(key)):continue
        status=str(entry.get('status') or '')
        q=queue.get(key,{})
        references=reference_urls(q,language)
        group=classify(status,entry,q,references)
        if not group:continue
        card,var=key
        readiness=filter_readiness.analyze(q) if q else {'missing':[],'unsupported':[]}
        item={'printStamp':str(q.get('stempel') or '[]'),'printFoil':str(q.get('foil') or ''),
          'referenceUrl':str(q.get('reference_product_url') or ''),
          'missingFields':entry.get('missing_fields') or readiness['missing'],
          'unfilterablePrintFeatures':readiness['unsupported'],
          'cardId':card,'variantId':var,'setId':q.get('set_id') or entry.get('set_id') or card.rsplit('-',1)[0],
          'name':q.get('kartenname_suche') or entry.get('name') or card,
          'language':language,'status':status,'type':group,
          'detail':str(entry.get('error') or entry.get('pagination_failure') or entry.get('reason') or '')[:220],
          'productId':str(entry.get('product_id') or ''), 'seenAt':entry.get('seen_at') or '',
          'scoreMatchState':str(entry.get('score_matching_status') or ''),
          'scorePageCandidateOnly':entry.get('score_page_candidate_only') is True,
          'scoreCandidateUrls':[u for u in (references or entry.get('score_top_candidate_urls') or [])[:CANDIDATE_URL_LIMIT]
             if isinstance(u,str) and u.startswith('https://www.cardmarket.com/')],
          'filterMode':str(entry.get('filter_mode') or ''),
          'officialProductGuide':entry.get('official_guide_product_aggregate') or None,
          'specialPrintComments':entry.get('special_print_comment_evidence') or None}
        if search.strip() and search.strip().casefold() not in ' '.join(str(v) for v in item.values()).casefold():continue
        if for_export:
            item.update(
                cardNumber=q.get('kartennummer') or entry.get('number') or '',
                printType=q.get('drucktyp') or '',
                specialPrint=q.get('sonderdruck') or '',
                productUrl=entry.get('url') or '',
                searchQuery=entry.get('query') or '',
                scoreCandidateCount=entry.get('score_candidate_count'),
            )
        output.append(item)
    output.sort(key=lambda e:e['seenAt'],reverse=True)
    full_counts={'assignment':sum(x['type']=='ZUORDNUNG' for x in output),
            'technical':sum(x['type']=='TECHNISCH' for x in output),
            'printChecks':sum(x['type']=='DRUCKPRUEFUNG' for x in output),
            'priceChecks':sum(x['type']=='PREISPRUEFUNG' for x in output),
            'missingData':sum(x['type']=='DATEN_FEHLEN' for x in output)}
    if kind=='karten':output=[x for x in output if x['type'] in ('ZUORDNUNG','DATEN_FEHLEN')]
    elif kind=='preise':output=[x for x in output if x['type']=='PREISPRUEFUNG']
    elif kind=='technik':output=[x for x in output if x['type']=='TECHNISCH']
    elif kind=='drucke':output=[x for x in output if x['type']=='DRUCKPRUEFUNG']
    return {'language':language,'scope':scope,'kind':kind,'total':len(output),'page':page,'pageSize':50,
            **full_counts,
            'items':output if for_export else output[page*50:(page+1)*50]}

def csv_cell(value):
    if isinstance(value, list):
        value = ' | '.join(map(str, value))
    text = '' if value is None else str(value)
    # Prevent spreadsheet software from evaluating text from scanner logs.
    if text.startswith(('\t', '\r', '\n')) or text.lstrip().startswith(('=', '+', '-', '@', '＝', '＋', '－', '＠')):
        return "'" + text
    return text


def write_failures_csv(items, stream):
    stream.write('\ufeff')
    writer = csv.writer(stream, delimiter=';', lineterminator='\r\n')
    candidate_headers = [f'Kandidat {i}' for i in range(1, CANDIDATE_URL_LIMIT + 1)]
    writer.writerow([label for label, _ in CSV_COLUMNS] + candidate_headers)
    for item in items:
        row = [csv_cell(item.get(key)) for _, key in CSV_COLUMNS]
        candidates = item['scoreCandidateUrls']
        row.extend(csv_cell(url) for url in candidates)
        row.extend([''] * (CANDIDATE_URL_LIMIT - len(candidates)))
        writer.writerow(row)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', choices=['de', 'en'], default='de')
    parser.add_argument('--scope', choices=['all', 'current'], default='current')
    parser.add_argument('--page', type=int, default=0)
    parser.add_argument('--search', default='')
    parser.add_argument('--kind', choices=['karten', 'preise', 'technik', 'drucke', 'alle'], default='karten')
    parser.add_argument('--format', choices=['json', 'csv'], default='json')
    args = parser.parse_args()
    exporting = args.format == 'csv'
    result = list_failures(
        language=args.language, page=args.page, search=args.search, scope=args.scope,
        kind=args.kind, for_export=exporting,
    )
    if exporting:
        _cm_sys.stdout.reconfigure(encoding='utf-8', newline='')
        write_failures_csv(result['items'], _cm_sys.stdout)
    else:
        print(json.dumps(result, ensure_ascii=False))
