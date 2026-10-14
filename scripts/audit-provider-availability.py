#!/usr/bin/env python3
"""Read-only availability test for documented pricing feeds."""
import json
from pathlib import Path
import requests
SOURCES={
"pokemontcgapi_sources":"https://api.pokemontcgapi.com/v1/prices/sources",
"pokemontcgapi_plans":"https://api.pokemontcgapi.com/v1/billing/plans",
"pokemontcg_io":"https://api.pokemontcg.io/v2/cards/base1-4",
"tcgcsv":"https://tcgcsv.com/tcgplayer/3/1423/prices",
"cardmarket_catalog":"https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json",
"cardmarket_guide":"https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json"
}
def check(name,url):
    try:
        method=requests.head if name.startswith("cardmarket") else requests.get
        r=method(url,headers={"User-Agent":"Cardyssey/1.0 (https://cardyssey.de)"},timeout=15)
        return dict(http=r.status_code,available=r.ok,bytes=len(r.content))
    except requests.RequestException as e:
        return dict(available=False,error=type(e).__name__)
if __name__=="__main__":
    outcome={name:check(name,url) for name,url in SOURCES.items()}
    Path("/tmp/cardyssey-provider-access-audit.json").write_text(json.dumps(outcome,indent=2))
    print(json.dumps(outcome,indent=2))
