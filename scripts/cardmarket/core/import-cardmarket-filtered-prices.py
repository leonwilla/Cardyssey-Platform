#!/usr/bin/env python3
"""Publish one filtered asking median per card variant and language.

Verified standard prints may use a sample that reached the paging limit.
Other prints require complete offers and a matching human-confirmed route.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse,csv,json,math,re,subprocess
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
import importlib.util as _ilu
from cardmarket_price_sanity import browser_price_plausible
_gp_spec=_ilu.spec_from_file_location('_guide_prices',_cm_Path(__file__).resolve().parent/'publish-cardmarket-guide-prices.py')
_gp=_ilu.module_from_spec(_gp_spec);_gp_spec.loader.exec_module(_gp)
guide_value=_gp.guide_value

STANDARD_REVERSE_FILTER = {"normal":"N", "nonholo":"N", "common":"N", "holo":"N", "reverse":"Y"}
VERSIONED_PRODUCT = re.compile(r"(?:^|-)V[1-9][0-9]?(?:-|$)", re.IGNORECASE)
FIRST_EDITION = re.compile(r"\b(?:1st[ ._-]*edition|first[ ._-]*edition|1\.?\s*auflage)\b", re.IGNORECASE)
VERIFIED_FILTER_MODES = {"CANONICAL_URL_DOM_VERIFIED", "FORM_SUBMISSION_DOM_VERIFIED"}


def standard_catalog(directory, language):
    """Read the same verified-set and per-variant evidence used by the collector."""
    guards = {}
    observed = directory / "observed-set-url-guards.json"
    if observed.is_file():
        evidence = json.loads(observed.read_text(encoding="utf-8-sig"))
        if evidence.get("minimumDistinctCards", 0) >= 5:
            guards.update({
                key: item["setSlug"] for key, item in evidence.get("setSlugs", {}).items()
                if item.get("distinctLiveCards", 0) >= 5
                and item.get("proof") == "OFFICIAL_PRODUCT_ID_AND_LIVE_NUMBER_AND_UNIQUE_SET_PATH"
                and re.fullmatch(r"[A-Za-z0-9-]{2,90}", item.get("setSlug") or "")
            })
    indexed = directory / "index-set-url-guards.json"
    if indexed.is_file():
        evidence = json.loads(indexed.read_text(encoding="utf-8-sig"))
        if evidence.get("schema") == 1 and evidence.get("source") == "CARDMARKET_EXPANSION_LIST_OFFICIAL_PRODUCT_IDS":
            for key, slug in (evidence.get("setSlugs") or {}).items():
                if key not in guards and re.fullmatch(r"[A-Za-z0-9-]{2,90}", slug or ""):
                    guards[key] = slug
    verified = directory / "verified-set-url-guards.json"
    if verified.is_file():
        guards.update(json.loads(verified.read_text(encoding="utf-8-sig")))

    rows = {}
    first_edition_sets = set()
    for queue_language in ("de", "en"):
        queue = directory / f"queue-{queue_language}.csv"
        if not queue.is_file():
            continue
        with queue.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if queue_language == language:
                    rows[(row["cardyssey_karte"], row["variante_id"])] = row
                if FIRST_EDITION.search(f"{row.get('stempel') or ''} {row.get('sonderdruck') or ''}"):
                    first_edition_sets.add(row.get("set_id"))
    return rows, guards, first_edition_sets


INDEX_DIRECT = ("DIRECT_PRODUCT_URL", "DIRECT_PRODUCT_URL_ID_CORRECTED", "DIRECT_PRODUCT_URL_RULE",
                "DIRECT_PRODUCT_URL_VARIANT_ID")


def is_standard(x, row, set_slug, first_edition_sets, path_parts, product_id):
    if not row or not set_slug or len(path_parts) != 7 or path_parts[-2].casefold() != set_slug.casefold():
        return False
    # Expansion-list index: Cardmarket's own list proved this product for this
    # printed number, and the variant is distinguishable by the offer filters
    # (or mapped by a per-set version rule). Foil/stamp names and V1/V2
    # versions are then not a reason to hold the price back.
    indexed = (row.get("index_status") in INDEX_DIRECT and row.get("index_product_id") == product_id
               and row.get("catalog_singleton_id") == product_id
               and "/".join(path_parts[-2:]) == "/".join(str(row.get("index_product_url") or "").split("/")[-2:]))
    if (row.get("set_id") != x.get("set_id") or row.get("kartennummer") != x.get("number")
        or not row.get("kartennummer") or x.get("card_number_url_verified") is not True
        or row.get("catalog_singleton_id") != product_id
        or not str(row.get("catalog_expansion_id") or "").isdecimal()
        or row.get("candidate_status") == "SET_EXPANSION_AMBIGUOUS"):
        return False
    if not indexed and (not {"foil", "stempel", "sonderdruck"}.issubset(row)
        or (row.get("foil") or "").strip() or (row.get("sonderdruck") or "").strip()
        or (row.get("stempel") or "").strip().lower() not in ("", "[]", "null")
        or x.get("observed_url_version") or VERSIONED_PRODUCT.search(path_parts[-1])
        or x.get("version_family_candidate_used") or x.get("stamp_route")
        or x.get("non_filterable_print_attributes")):
        return False
    if indexed and (x.get("stamp_route") or x.get("version_family_candidate_used")):
        return False
    reverse = STANDARD_REVERSE_FILTER.get((row.get("drucktyp") or "").strip().lower())
    if reverse is None or reverse != x.get("expected_reverse_holo"):
        return False
    first = x.get("expected_first_edition")
    if first == "0":
        # Either language's catalog can establish that the expansion has a
        # separate First Edition print and therefore needs an explicit filter.
        return row["set_id"] not in first_edition_sets
    if indexed:
        # 1st edition and unlimited are explicit Cardmarket offer filters.
        return first in ("Y", "N")
    return first == "N" and x.get("exact_print_filter_supported") is not False


def collect(path,language,now=None,guides=None,rejected=None):
    """guides: {idProduct: Preisführer-Eintrag}; unplausible Preise landen in rejected (Liste)."""
    if language not in ('de','en'):raise ValueError('language')
    now=now or datetime.now(timezone.utc)
    latest={}
    with path.open(encoding='utf-8-sig') as f:
        for line in f:
            try:
                x=json.loads(line)
                if x.get('card_id') and x.get('variant_id'):
                    latest[(x['card_id'],x['variant_id'])]=x
            except (ValueError,TypeError):continue
    catalog, set_slugs, first_edition_sets = standard_catalog(path.parent, language)
    results=[]
    for (card,variant),x in latest.items():
        if x.get("language") != language or x.get("identity_confirmed") is not True:
            continue
        complete = (x.get("status") == "COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED"
                    and x.get("all_pages_complete") is True)
        sampled = (x.get("status") == "FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE"
                   and x.get("all_pages_complete") is False
                   and x.get("pagination_failure") == "MORE_OFFERS_STILL_VISIBLE"
                   and type(x.get("offer_pages_attempted")) is int and x["offer_pages_attempted"] >= 3)
        if not complete and not sampled:
            continue
        median = x.get("median_all_offers_eur" if complete else "sample_median_eur")
        if isinstance(median,bool) or not isinstance(median,(float,int)) or not math.isfinite(median) or not 0<median<1e6:continue
        verified_offers = x.get("verified_lang_nm_offers")
        if type(verified_offers) is not int or verified_offers < 1:
            continue
        if sampled and (verified_offers < 20 or type(x.get("offers_seen")) is not int
                        or x["offers_seen"] != verified_offers or x.get("access_mode") != "AUTHENTICATED"):
            continue

        url=str(x.get('url') or '')
        u=urlsplit(url)
        if u.scheme!='https' or u.netloc!='www.cardmarket.com' or not u.path.startswith('/'+language+'/Pokemon/Products/Singles/'):
            continue
        pid=str(x.get('product_id') or '')
        if not pid.isdecimal():continue
        reverse=x.get('expected_reverse_holo')
        first=x.get('expected_first_edition')
        q=parse_qs(u.query, keep_blank_values=True)
        url_filtered = (q.get("language") == (["3"] if language == "de" else ["1"])
                        and q.get("minCondition") == ["2"] and q.get("isReverseHolo") == [reverse]
                        and q.get("isFirstEd") in ((None, ["0"]) if first == "0" else ([first],)))
        # Current collectors store the canonical product URL and separately
        # attest that the offer DOM and filters were verified.
        combined = x.get("filter_mode") == "COMBINED_URL_DOM_VERIFIED"
        combined_verified = False
        if combined:
            source = urlsplit(str(x.get("source_product_url") or ""))
            combined_verified = (
                x.get("source_filter_language_ids") == "1,3"
                and str(x.get("combined_product_id_verified") or "") == pid
                and source.scheme == "https" and source.netloc == "www.cardmarket.com"
                and source.path.startswith(("/de/Pokemon/Products/Singles/", "/en/Pokemon/Products/Singles/"))
                and source.path[3:] == u.path[3:] and not source.query
                and type(x.get("combined_offers_seen")) is int
                and x["combined_offers_seen"] >= x.get("offers_seen", 0)
            )
            if not combined_verified:
                continue
        dom_filtered = not u.query and (x.get("filter_mode") in VERIFIED_FILTER_MODES or combined_verified)
        automatic = ((url_filtered or dom_filtered)
                     and is_standard(x, catalog.get((card, variant)), set_slugs.get(x.get("set_id")),
                                     first_edition_sets, unquote(u.path).split("/"), pid))
        if not automatic:
            # Keep the original explicit filter requirements for human routes.
            if (not complete or not url_filtered or reverse not in ("Y", "N") or first not in ("Y", "N")
                or x.get("non_filterable_print_attributes") or x.get("exact_print_filter_supported") is False):
                continue
        try:seen=datetime.fromisoformat(str(x.get('seen_at') or '').replace('Z','+00:00')).astimezone(timezone.utc)
        except (ValueError,TypeError):continue
        if seen<now-timedelta(days=8) or seen>now+timedelta(hours=1):continue
        if guides is not None:
            guide_eur,_=guide_value(guides.get(int(pid)) or {}, reverse=="Y")
            ok,why=browser_price_plausible(median,guide_eur,first_edition=(first=="Y"),offers=verified_offers)
            if not ok:
                if rejected is not None:
                    rejected.append({'card':card,'variant':variant,'price':median,'guide':guide_eur,'reason':why})
                continue
        results.append({'language':language,'card':card,'variant':variant,
            'product_id':pid,'url':url.split('?')[0],'price':round(median,4),'observed_at':seen.isoformat(),
            'automatic_standard':automatic,'page_limited_sample':sampled})
    return results

SQL="""
WITH rows AS (
 SELECT item->>'language' AS lang,item->>'card' AS card,item->>'variant' AS variant,
 item->>'product_id' AS pid,item->>'url' AS url,(item->>'price')::numeric AS price,
 (item->>'observed_at')::timestamptz AS observed,
 item->>'automatic_standard'='true' AS automatic_standard
 FROM jsonb_array_elements({payload}::jsonb) item
), routed AS (
 SELECT r.*,p.verification_state,p.source_evidence,
   (p.primary_provider='CARDMARKET' AND p.provider_product_id=r.pid
    AND (p.provider_product_url IS NULL OR p.provider_product_url='' OR split_part(p.provider_product_url,'?',1)=r.url)) AS matches_route
 FROM rows r LEFT JOIN price_source_routing p
 ON p.language_code=r.lang AND p.card_id=r.card AND p.variant_id=r.variant
), approved AS (
 SELECT * FROM routed
 WHERE (verification_state='VERIFIED_PRODUCT_ID' AND matches_route AND source_evidence LIKE 'Human confirmed exact%')
    OR (automatic_standard AND (verification_state IS DISTINCT FROM 'VERIFIED_PRODUCT_ID' OR matches_route))
), compatible AS (
 SELECT r.*, COALESCE(cached.legacy_variant, print.legacy_variant) AS legacy_variant
 FROM approved r
 LEFT JOIN tcg_price_cache cached
   ON cached.language_code=r.lang AND cached.card_id=r.card AND cached.variant_id=r.variant
 LEFT JOIN catalog_cards_mirror c
   ON c.language_code=r.lang AND c.card_id=r.card AND cached.card_id IS NULL
 LEFT JOIN LATERAL (
   SELECT value->>'legacyVariant' AS legacy_variant
   FROM jsonb_array_elements(c.variants) AS value
   WHERE value->>'id'=r.variant
   LIMIT 1
 ) print ON TRUE
)
INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,source,base_eur,updated_at,resolution_status)
SELECT card,lang,variant,legacy_variant,
 CASE WHEN lang='de' THEN 'CARDMARKET_DE_NM_WEB' ELSE 'CARDMARKET_EN_NM_WEB' END,
 price,observed,'PRICE_FOUND' FROM compatible
WHERE legacy_variant IN ('NORMAL','HOLO','REVERSE')
ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET
 source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,
 updated_at=EXCLUDED.updated_at,resolution_status='PRICE_FOUND',failure_detail=NULL
WHERE tcg_price_cache.updated_at<=EXCLUDED.updated_at;
"""

def apply(rows):
    for i in range(0,len(rows),100):
        data=json.dumps(rows[i:i+100],ensure_ascii=False,separators=(',',':')).replace("'","''")
        sql='BEGIN;\n'+SQL.format(payload="'"+data+"'")+'\nCOMMIT;'
        subprocess.run(['docker','exec','-i','cardyssey-db','psql','-X','-q','-v','ON_ERROR_STOP=1',
                        '-U','cardyssey','-d','cardyssey'],input=sql,text=True,check=True,stdout=subprocess.DEVNULL)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--language',choices=('de','en'),required=True)
    p.add_argument('--results',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    guides=None
    try:
        from price_feed_client import fetch_json
        from cardmarket_game_profile import load_game_profile
        guides={x['idProduct']:x for x in fetch_json(load_game_profile()['price_url'])['priceGuides']}
    except Exception:
        guides=None  # ohne Preisführer keine Plausibilitätsprüfung, Import läuft wie bisher
    rejected=[]
    rows=collect(a.results,a.language,guides=guides,rejected=rejected)
    if a.apply and rows:apply(rows)
    print(json.dumps({'language':a.language,'implausible_rejected':len(rejected),
       'full_filtered_candidates':sum(not row['page_limited_sample'] for row in rows),
       'page_limited_standard_candidates':sum(row['page_limited_sample'] for row in rows),
       'automatic_standard_candidates':sum(row['automatic_standard'] for row in rows),
       'apply':a.apply,'basis':'filtered_active_asking_median_not_sold'}))
