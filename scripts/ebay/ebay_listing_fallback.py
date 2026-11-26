#!/usr/bin/env python3
"""eBay offers (with links) for DE/EN card variants.

Decision 26.11.2026: eBay asking prices are NOT used as a price (checked
against Cardmarket: only ~half within +-50 %). They are stored and shown in
the card window as "Angebote auf eBay" with links. Real eBay values need sold
data (Marketplace Insights).

Uses the official eBay Browse API (keys in ~/.config/cardyssey/ebay.env,
Production keyset "Cardyssey Preise"). One search per card on eBay.de, then
strict title matching per variant (scripts/ebay/ebay_listing_match.py).
The price is the median of all matching Buy-It-Now offers (asking prices,
not sales) and needs at least three offers.

Cardmarket always wins: a variant with a Cardmarket price is never touched,
and the Cardmarket jobs overwrite an eBay fallback as soon as they have one.
Uncertain prints (set logo stamp, player rewards, copyright 1999-2000) are
computed for review only. World Championship deck prints are skipped.

  --dry-run --limit 40     search and print, write nothing
  --apply                  store offers + fallback prices
"""
import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ebay_listing_match as em  # noqa: E402

KEYS = Path.home() / ".config/cardyssey/ebay.env"
STATE = Path.home() / ".local/state/cardyssey-ebay-fallback.json"
CATEGORY = "183454"  # CCG Individual Cards
DAILY_CALLS = 4500   # eBay allows 5,000 Browse calls per day for this keyset
REFRESH_DAYS = 14


def psql(sql, stdin=None):
    cmd = ["docker", "exec", "-i", "cardyssey-db", "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1",
           "-U", "cardyssey", "-d", "cardyssey", "-At", "-c", sql] if stdin is None else \
          ["docker", "exec", "-i", "cardyssey-db", "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1",
           "-U", "cardyssey", "-d", "cardyssey", "-At"]
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True, check=True).stdout


def lit(value):
    return "'" + str(value).replace("'", "''") + "'"


TARGETS = """
SELECT json_build_object('lang',c.language_code,'card',c.card_id,'name',c.name,'number',c.local_id,
  'set',c.set_id,'setName',s.name,'total',s.official_count,'enName',e.name,'deName',d.name,
  'variants',c.variants,
  'missing',(SELECT json_agg(v->>'id') FROM jsonb_array_elements(c.variants) v
             LEFT JOIN tcg_price_cache p ON p.language_code=c.language_code AND p.card_id=c.card_id
                                         AND p.variant_id=v->>'id'
             LEFT JOIN global_price_source_policy g ON g.language_code=c.language_code
                                         AND g.card_id=c.card_id AND g.variant_id=v->>'id'
             WHERE NOT (p.resolution_status='PRICE_FOUND' AND COALESCE(p.base_eur,0)>0)
                OR COALESCE(g.price_class,'') <> 'BULK'),
  'noPrice',(SELECT count(*) FROM jsonb_array_elements(c.variants) v
             LEFT JOIN tcg_price_cache p ON p.language_code=c.language_code AND p.card_id=c.card_id
                                         AND p.variant_id=v->>'id'
             WHERE NOT (p.resolution_status='PRICE_FOUND' AND COALESCE(p.base_eur,0)>0)),
  'checked',(SELECT min(o.checked_at) FROM ebay_listing_offers o
             WHERE o.language_code=c.language_code AND o.card_id=c.card_id))
FROM catalog_cards_mirror c
LEFT JOIN catalog_sets_mirror s ON s.language_code=c.language_code AND s.set_id=c.set_id
LEFT JOIN catalog_cards_mirror e ON e.language_code='en' AND e.card_id=c.card_id
LEFT JOIN catalog_cards_mirror d ON d.language_code='de' AND d.card_id=c.card_id
WHERE c.language_code IN ('de','en') AND c.set_id !~* '^(A[0-9]|B[0-9]|P-A)'
"""


ASIA_INFO = Path.home() / ".local/state/cardtrader-asia-cards.json"
ASIA_TARGETS = """
SELECT json_build_object('lang',c.language_code,'card',c.card_id,'number',c.local_id,'set',c.set_id,
  'total',s.official_count,'setName',NULL,'variants',c.variants,
  'missing',(SELECT json_agg(v->>'id') FROM jsonb_array_elements(c.variants) v
             LEFT JOIN tcg_price_cache p ON p.language_code=c.language_code AND p.card_id=c.card_id
                                         AND p.variant_id=v->>'id'
             WHERE NOT (p.resolution_status='PRICE_FOUND' AND COALESCE(p.base_eur,0)>0)),
  'noPrice',1,
  'checked',(SELECT min(o.checked_at) FROM ebay_listing_offers o
             WHERE o.language_code=c.language_code AND o.card_id=c.card_id))
FROM catalog_cards_mirror c
LEFT JOIN catalog_sets_mirror s ON s.language_code=c.language_code AND s.set_id=c.set_id
WHERE c.language_code IN ('ja','ko','zh-tw')
"""
RARE_ASIA = {"rare", "holo rare", "ultra rare", "secret rare", "illustration rare", "special illustration rare",
             "hyper rare", "shiny holo rare", "shiny rare", "double rare", "art rare", "super rare",
             "character rare", "character super rare", "trainer gallery rare", "ace spec rare", "promo",
             "amazing rare", "radiant rare", "rare holo", "prism rare", "rainbow rare"}


def load_asia_targets(languages):
    """Rare Japanese/Korean/Chinese cards without a price; English name from
    CardTrader (our Japanese catalog names are not searchable on eBay)."""
    try:
        info = json.loads(ASIA_INFO.read_text())
    except (OSError, ValueError):
        return []
    rows = []
    for line in psql(ASIA_TARGETS).splitlines():
        x = json.loads(line)
        ct = info.get(f"{x['lang']}|{x['card']}") or {}
        if x["lang"] not in languages or not x["missing"] or not ct.get("name"):
            continue
        if str(ct.get("rarity") or "").lower() not in RARE_ASIA:
            continue
        x.update(name=ct["name"], enName=None, deName=None, setName=ct.get("exp") or x["set"])
        rows.append(x)
    return rows


def load_targets(languages):
    rows = []
    for line in psql(TARGETS).splitlines():
        x = json.loads(line)
        if x["lang"] in languages and x["missing"]:
            rows.append(x)
    return rows


class Ebay:
    def __init__(self):
        kv = dict(l.strip().split("=", 1) for l in KEYS.read_text().splitlines() if l.startswith("EBAY_"))
        self.auth = base64.b64encode(f"{kv['EBAY_CLIENT_ID']}:{kv['EBAY_CLIENT_SECRET']}".encode()).decode()
        self.token, self.expires, self.calls = None, 0, 0

    def _token(self):
        if self.token and time.time() < self.expires - 120:
            return self.token
        req = urllib.request.Request(
            "https://api.ebay.com/identity/v1/oauth2/token",
            data=urllib.parse.urlencode({"grant_type": "client_credentials",
                                         "scope": "https://api.ebay.com/oauth/api_scope"}).encode(),
            headers={"Authorization": "Basic " + self.auth, "Content-Type": "application/x-www-form-urlencoded"})
        d = json.load(urllib.request.urlopen(req, timeout=30))
        self.token, self.expires = d["access_token"], time.time() + int(d.get("expires_in", 7200))
        return self.token

    def search(self, query, marketplace="EBAY_DE", currency="EUR"):
        params = {"q": query, "category_ids": CATEGORY, "limit": "200", "sort": "price",
                  "filter": f"buyingOptions:{{FIXED_PRICE}},conditionIds:{{4000}},priceCurrency:{currency}"}
        req = urllib.request.Request(
            "https://api.ebay.com/buy/browse/v1/item_summary/search?" + urllib.parse.urlencode(params),
            headers={"Authorization": "Bearer " + self._token(), "X-EBAY-C-MARKETPLACE-ID": marketplace,
                     "Accept-Language": "de-DE" if marketplace == "EBAY_DE" else "en-US"})
        self.calls += 1
        for attempt in range(3):
            try:
                return json.load(urllib.request.urlopen(req, timeout=30)).get("itemSummaries") or []
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    time.sleep(10 * (attempt + 1))
                    continue
                raise
        return []


_USD_EUR = None


def usd_eur():
    """ECB reference rate via frankfurter.dev (cached per run)."""
    global _USD_EUR
    if _USD_EUR is None:
        d = json.load(urllib.request.urlopen("https://api.frankfurter.dev/v2/rate/USD/EUR", timeout=20))
        _USD_EUR = float(d.get("rate") or d["rates"]["EUR"])
    return _USD_EUR


def search_card(ebay, card):
    """Asian cards are listed far more on eBay.com (30-card test: 23 vs 3
    cards with offers); their USD prices are converted with the ECB rate."""
    if card["lang"] in ("ja", "ko", "zh-tw"):
        rate = usd_eur()
        items = ebay.search(query_for(card), "EBAY_US", "USD")
        for it in items:
            price = it.get("price") or {}
            if price.get("currency") == "USD":
                it["price"] = {"value": round(float(price["value"]) * rate, 2), "currency": "EUR"}
        return items
    return ebay.search(query_for(card))


def query_for(card):
    number = str(card["number"] or "").strip()
    total = card.get("total")
    plain = number.isdigit()
    num = f"{number}/{total}" if plain and total else number
    if card["lang"] in ("ja", "ko", "zh-tw"):
        word = {"ja": "japanese", "ko": "korean", "zh-tw": "chinese"}[card["lang"]]
        return f"{card['name']} {num} {word}"
    return f"{card['name']} {num}"


def evaluate(card, items):
    """Per missing variant: spec status, matching offers, fallback price."""
    variants = {v["id"]: v for v in card["variants"] or []}
    other = (card.get("enName") if card["lang"] == "de" else card.get("deName")) if card["lang"] in ("de", "en") else None
    names = [n for n in (card["name"], other) if n]
    set_words = [w for w in em.norm(card.get("setName") or "").split() if len(w) > 3]
    out = []
    for vid in card["missing"]:
        v = variants.get(vid)
        if not v:
            continue
        siblings = [s for s in variants.values() if s["id"] != vid]
        spec, status = em.variant_spec(v, siblings)
        # Two variants a title cannot tell apart never get the same guessed price.
        if spec is not None and any(em.signature(s) == em.signature(v) for s in siblings):
            status = "UNCERTAIN"
        if spec is None:
            out.append({"variant": vid, "status": status, "offers": [], "price": None})
            continue
        offers = []
        for it in items:
            price = it.get("price") or {}
            if price.get("currency") != "EUR":
                continue
            if em.matches(it.get("title", ""), language=card["lang"], names=names, number=card["number"],
                          total=card.get("total"), set_words=set_words, spec=spec, set_id=card["set"]):
                offers.append({"title": it.get("title", "")[:160], "eur": float(price["value"]),
                               "url": (it.get("itemWebUrl") or "").split("?")[0], "itemId": it.get("itemId")})
        offers.sort(key=lambda o: o["eur"])
        out.append({"variant": vid, "status": status, "spec": spec, "offers": offers,
                    "price": em.fallback_price([o["eur"] for o in offers])})
    return out


SAVE = """
WITH x AS (SELECT * FROM jsonb_to_recordset({payload}::jsonb)
           AS x(card text, variant text, price numeric, n int, status text, offers jsonb, query text))
INSERT INTO ebay_listing_offers(language_code,card_id,variant_id,price_eur,offer_count,match_status,listings,query,checked_at)
SELECT {lang},card,variant,price,n,status,offers,query,NOW() FROM x
ON CONFLICT(language_code,card_id,variant_id) DO UPDATE SET price_eur=EXCLUDED.price_eur,
  offer_count=EXCLUDED.offer_count, match_status=EXCLUDED.match_status, listings=EXCLUDED.listings,
  query=EXCLUDED.query, checked_at=EXCLUDED.checked_at;
"""


def save(lang, rows):
    for i in range(0, len(rows), 300):
        payload = lit(json.dumps(rows[i:i + 300], ensure_ascii=False))
        psql(None, stdin="BEGIN;\n" + SAVE.format(payload=payload, lang=lit(lang)) + "\nCOMMIT;")


def load_state():
    try:
        s = json.loads(STATE.read_text())
    except (OSError, ValueError):
        s = {}
    today = datetime.now(timezone.utc).date().isoformat()
    if s.get("day") != today:
        s = {"day": today, "calls": 0}
    return s


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=0, help="max cards this run")
    p.add_argument("--language", choices=("de", "en", "ja", "ko", "zh-tw"), action="append")
    p.add_argument("--cards", help="comma separated card IDs (test)")
    a = p.parse_args()
    languages = a.language or ["de", "en", "ja", "ko", "zh-tw"]
    state = load_state()
    budget = DAILY_CALLS - state["calls"]
    now = datetime.now(timezone.utc)
    cards = load_targets([l for l in languages if l in ("de", "en")]) + \
        load_asia_targets([l for l in languages if l not in ("de", "en")])
    if a.cards:
        wanted = set(a.cards.split(","))
        cards = [c for c in cards if c["card"] in wanted]
    else:
        # Never checked first, then the oldest check; skip fresh ones.
        def age(c):
            if not c["checked"]:
                return float("inf")
            return (now - datetime.fromisoformat(c["checked"])).total_seconds()
        cards = [c for c in cards if age(c) > REFRESH_DAYS * 86400]
        # Cards without a Cardmarket price first, then the oldest check.
        cards.sort(key=lambda c: (c["noPrice"] == 0, -min(age(c), 1e12)))
    if a.limit:
        cards = cards[:a.limit]
    cards = cards[:max(0, budget)]
    ebay = Ebay()
    stats = {"cards": 0, "variants": 0, "priced": 0, "uncertain": 0, "skipped": 0, "too_few": 0}
    # "priced" = at least three matching offers (shown with links, no price).
    pending = {"de": [], "en": [], "ja": [], "ko": [], "zh-tw": []}
    for card in cards:
        query = query_for(card)
        items = search_card(ebay, card)
        stats["cards"] += 1
        for r in evaluate(card, items):
            stats["variants"] += 1
            key = {"OK": "priced" if r["price"] is not None else "too_few",
                   "UNCERTAIN": "uncertain", "SKIP": "skipped"}[r["status"]]
            stats[key] += 1
            if a.dry_run:
                print(f"{card['lang']} {card['card']} {card['name']} | {query} | {r['variant']} "
                      f"{r['status']} {r.get('spec')} -> {r['price']} ({len(r['offers'])} Angebote)")
                for o in r["offers"][:3]:
                    print(f"      {o['eur']:>8.2f}  {o['title'][:90]}")
            pending[card["lang"]].append({"card": card["card"], "variant": r["variant"], "price": r["price"],
                                          "n": len(r["offers"]), "status": r["status"],
                                          "offers": r["offers"][:5], "query": query})
        time.sleep(0.3)
    if a.apply:
        for lang, rows in pending.items():
            if rows:
                save(lang, rows)
        state["calls"] += ebay.calls
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state))
    stats["apiCalls"] = ebay.calls
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
