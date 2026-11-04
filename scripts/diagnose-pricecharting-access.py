#!/usr/bin/env python3
"""Safe PriceCharting connector preflight.

Never disable TLS verification, use an untrusted subdomain as an API endpoint,
forward authentication cookies, or treat a challenge page as a price source.
"""
import argparse,csv,datetime,json,os,ssl,socket,urllib.request,urllib.error
from pathlib import Path

OFFICIAL='https://www.pricecharting.com/'
ALTERNATE='https://ae.pricecharting.com/'
ROOT=Path(__file__).resolve().parents[1]
MAPPING=ROOT/'config/pricecharting-exact-variants.csv'


def probe(url,timeout=10):
    request=urllib.request.Request(url,headers={'User-Agent':'Cardyssey source-health-check/1.0','Accept':'text/html'})
    try:
        with urllib.request.urlopen(request,timeout=timeout,context=ssl.create_default_context()) as response:
            body=response.read(2048)
            resolved=response.geturl()
            result={'status':'OK','httpStatus':response.status,'finalUrl':resolved}
            if b'Just a moment' in body or b'cf-chl' in body:
                result['status']='CHALLENGE'
            if not resolved.startswith(OFFICIAL):
                result['status']='UNEXPECTED_DESTINATION'
            return result
    except urllib.error.HTTPError as err:
        status='CHALLENGE_OR_FORBIDDEN' if err.code in (401,403,429) else 'HTTP_ERROR'
        return {'status':status,'httpStatus':err.code,'finalUrl':err.geturl()}
    except urllib.error.URLError as err:
        if isinstance(err.reason,ssl.SSLCertVerificationError):
            return {'status':'TLS_CERTIFICATE_INVALID'}
        return {'status':'NETWORK_ERROR','errorType':type(err.reason).__name__}
    except (TimeoutError,OSError) as err:
        return {'status':'NETWORK_ERROR','errorType':type(err).__name__}


def preflight(prober=probe):
    mappings=0
    verified=0
    if MAPPING.exists():
        with MAPPING.open(newline='') as handle:
            rows=list(csv.DictReader(handle))
            mappings=len(rows)
            verified=sum(x.get('identity_verified','').strip().lower()=='true' for x in rows)
    main=prober(OFFICIAL)
    sub=prober(ALTERNATE)
    can_import=bool(os.environ.get('PRICECHARTING_API_KEY','').strip()) and verified>0
    return {
        'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'mainSite':main,'suggestedSubdomain':sub,
        'paidApiKeyConfigured':bool(os.environ.get('PRICECHARTING_API_KEY','').strip()),
        'mappedProducts':mappings,'verifiedProductMappings':verified,
        'apiImportPrerequisitesMet':can_import,
        'recommendation':('USE_OFFICIAL_API_ONLY' if can_import else 'NEEDS_LICENSED_API_ACCESS_AND_VERIFIED_PRODUCT_IDS'),
        'safety':'TLS verification mandatory; do not send cookies/tokens to alternate subdomains; no prices extracted from blocked pages'
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,default=Path('/tmp/cardyssey-pricecharting-access.json'))
    args=parser.parse_args()
    result=preflight()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
