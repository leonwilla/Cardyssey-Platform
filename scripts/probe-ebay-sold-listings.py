#!/usr/bin/env python3
"""Probe the DannyRivasDev sold-listings strategy without changing Cardyssey prices.

The 2023 example uses plain requests against /sch/i.html?LH_Sold=1&LH_Complete=1.
This diagnostic checks whether that HTML is actually available; HTTP 200 alone
does not imply that a real sold-results page was returned.
"""
import argparse
import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ENDPOINTS = ("www.ebay.com", "www.ebay.de")
BLOCK_MARKERS = ("captcha", "robot check", "access denied", "pardon our interruption", "verify you are a human")


def probe(host, query, timeout):
    params = urlencode({"_nkw": query, "_sacat": "0", "LH_Sold": "1", "LH_Complete": "1", "_pgn": "1"})
    url = f"https://{host}/sch/i.html?{params}"
    result = {"host": host, "url": url, "http_status": None, "status": "NETWORK_ERROR", "eligible_sold_listings": 0}
    try:
        req = Request(url, headers={"User-Agent": "CardysseyPriceSourceDiagnostics/1.0"})
        with urlopen(req, timeout=timeout) as response:
            body = response.read(1500000).decode("utf-8", errors="replace")
            result["http_status"] = response.status
            lower = body.lower()
            if any(marker in lower for marker in BLOCK_MARKERS):
                result["status"] = "BOT_CHALLENGE"
            elif 'class="srp-results' not in lower and 'class="s-item' not in lower:
                result["status"] = "NO_RESULTS_MARKUP"
            else:
                result["status"] = "HTML_AVAILABLE_REQUIRES_SOLD_IDENTITY_VERIFICATION"
    except HTTPError as exc:
        result["http_status"] = exc.code
        result["status"] = "ACCESS_BLOCKED" if exc.code in (403, 429) else "HTTP_ERROR"
    except (URLError, TimeoutError, OSError) as exc:
        result["error_type"] = type(exc).__name__
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="pokemon machamp 8/102")
    parser.add_argument("--timeout", type=float, default=12)
    parser.add_argument("--report")
    args = parser.parse_args()
    results = [probe(host, args.query, args.timeout) for host in ENDPOINTS]
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "reference": "https://github.com/DannyRivasDev/Ebay-Sold-Listings-Scraper",
        "method": "public_sold_search_http",
        "results": results,
        "price_cache_updated": False,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as file:
            file.write(output + "\n")
    print(output)


if __name__ == "__main__":
    main()
