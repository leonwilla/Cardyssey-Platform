"""Strict matching of eBay listing titles to one card variant.

Used for the eBay fallback price (only variants without a Cardmarket price).
Precision before recall: a listing counts only when the title names the card,
its printed number, the card language and exactly the variant's print
(Reverse, Pokeball pattern, 1st edition, ...). Graded cards, lots, proxies and
sealed products never count.
"""
import re
import unicodedata

# Print attributes a title can carry -> regex on the normalized title.
KEYWORDS = {
    "reverse": r"\breverse\b|\brev holo\b|\brh\b",
    "holo": r"\bholo\b|\bholofoil\b",
    "pokeball": r"\bpoke ?ball\b",
    "masterball": r"\bmaster ?ball\b|\bmeister ?ball\b",
    "friendball": r"\bfriend ?ball\b|\bfreundes ?ball\b",
    "duskball": r"\bdusk ?ball\b|\bfinster ?ball\b",
    "quickball": r"\bquick ?ball\b|\bflott ?ball\b",
    "loveball": r"\blove ?ball\b|\bsympa ?ball\b",
    "energy": r"\benergy (?:reverse|holo|pattern|symbol)\b|\benergie\b",
    "cosmos": r"\bcosmos\b|\bkosmos\b",
    "cracked": r"\bcracked ice\b",
    "first": r"\b1st\b|\b1 ?\.? ?auflage\b|\berste auflage\b|\bfirst edition\b|\b1 ?\.? ?edition\b",
    "shadowless": r"\bshadowless\b|\bschattenlos\b",
    "staff": r"\bstaff\b|\bmitarbeiter\b",
    "prerelease": r"\bpre ?release\b",
    "stamp": r"\bstamp(?:ed)?\b|\bstempel\b|\bgestempelt\b",
    "error": r"\bmisprint\b|\berror\b|\bfehldruck\b|\bfehlend\w*\b|\bno symbol\b|\bohne symbol\b|\bmissing\b",
}
PATTERNS = ("pokeball", "masterball", "friendball", "duskball", "quickball", "loveball", "energy", "cosmos", "cracked")
FOIL_KEYS = {
    "pokeball": "pokeball", "pokéball": "pokeball", "masterball": "masterball", "meisterball": "masterball",
    "friendball": "friendball", "freundesball": "friendball", "duskball": "duskball", "finsterball": "duskball",
    "quickball": "quickball", "flottball": "quickball", "loveball": "loveball", "sympaball": "loveball",
    "energy": "energy", "energie": "energy", "cosmos": "cosmos", "kosmos": "cosmos", "cracked-ice": "cracked",
}
# Never a single raw card of this print.
EXCLUDE = re.compile(
    r"\bpsa\b|\bbgs\b|\bcgc\b|\bbeckett\b|\bgraded\b|\bgegradet\b|\bgrading\b|\bslab\b|\bpca\b|\bgrade\b|"
    r"\blot\b|\bkonvolut\b|\bsammlung\b|\bbundle\b|\bplayset\b|\bset of\b|\b\d+ ?x\b|\bx ?\d+\b|\bstuck\b|"
    r"\bproxy\b|\bcustom\b|\bfan ?made\b|\bfanart\b|\borica\b|\bmetal\b|\breplica\b|\bfake\b|\bjumbo\b|"
    r"\boversize\b|\bbooster\b|\bdisplay\b|\betb\b|\bsealed\b|\bcode\b|\bsleeve\b|\bhulle\b|\bpin\b|"
    r"\bgold karte\b|\bgold card\b|\bwahl\b|\bauswahl\b|\bchoose\b|\bpick\b|\baussuchen\b|"
    r"\bmetall\b|\bfanartikel\b|\bgold foil\b|\bgold metal\b|\b24k\b|\bvergoldet\b|\bnachdruck\b|\breprint\b|"
    r"\bdamaged\b|\bpoor\b|\bbeschadigt\b|\bknick\w*\b|\bcrease\w*\b|\bbeschreibung lesen\b|\bread description\b"
)
# Reprint products that reuse the original number (30th Celebration, Celebrations
# Classic Collection); only allowed when the card itself belongs to them.
REPRINT = re.compile(r"\b30th\b|\banniversary\b|\bcelebrations?\b|\bclassic collection\b|\bjubil\w*\b")
REPRINT_SETS = ("30th", "cel25")
LANG_WORDS = {
    "de": r"\bdeutsch\b|\bgerman\b|\bde\b|\bger\b|\bdt\b",
    "en": r"\benglish\b|\benglisch\b|\beng\b|\ben\b",
    "ja": r"\bjapan\w*\b|\bjp\b|\bjpn\b|\bjap\b",
    "ko": r"\bkorea\w*\b|\bkr\b|\bkor\b",
    "zh-tw": r"\bchines\w*\b|\btraditional\b|\bt ?chinese\b|\btaiwan\w*\b|\bhong kong\b",
}
_ALL_LANGS = {"de": r"\bdeutsch\b|\bgerman\b", "en": r"\benglish\b|\benglisch\b|\beng\b",
              "ja": r"\bjapan\w*\b|\bjp\b|\bjpn\b", "ko": r"\bkorea\w*\b|\bkr\b",
              "zh-tw": r"\bchines\w*\b|\bsimplified\b", "fr": r"\bfranz\w*\b|\bfrench\b",
              "it": r"\bital\w*\b", "es": r"\bspan\w*\b", "pt": r"\bportug\w*\b"}
OTHER_LANG_BASE = {
    "de": r"\benglish\b|\benglisch\b|\beng\b|\bjap\w*\b|\bjp\b|\bkorea\w*\b|\bchines\w*\b|\bfranz\w*\b|"
          r"\bfrench\b|\bital\w*\b|\bspan\w*\b|\bportug\w*\b|\bniederl\w*\b|\bdutch\b",
    "en": r"\bdeutsch\b|\bgerman\b|\bjap\w*\b|\bjp\b|\bkorea\w*\b|\bchines\w*\b|\bfranz\w*\b|\bfrench\b|"
          r"\bital\w*\b|\bspan\w*\b|\bportug\w*\b|\bniederl\w*\b|\bdutch\b",
}
OTHER_LANG = dict(OTHER_LANG_BASE)
for _lang in ("ja", "ko", "zh-tw"):
    OTHER_LANG[_lang] = "|".join(v for k, v in _ALL_LANGS.items() if k != _lang)
# Variants we cannot tell apart reliably from titles: computed for review,
# never published automatically.
UNCERTAIN_STAMPS = {"set-logo", "player-rewards-program"}
UNCERTAIN_SUBTYPES = {"1999-2000-copyright", "copyright 1999-2000", "no-e-reader"}
# Stamps that are print attributes of regular TCG cards.
KNOWN_STAMPS = {"1st-edition", "1-auflage", "set-logo", "staff", "mitarbeiter", "pre-release", "prerelease",
                "player-rewards-program", "vorveroffentlichung"}
# Subtypes a title expresses (shadowless) or that only mean "the plain print".
PLAIN_SUBTYPES = {"", "unlimited", "unbegrenzt"}
SHADOWLESS = {"shadowless", "schattenlos"}


def _stamp(value):
    return norm(value).replace(" ", "-") if value else ""


def _sub(value):
    return norm(value) if value else ""


def norm(text):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    text = text.replace("&", " and ").replace("'", "")
    return " ".join(re.findall(r"[a-z0-9]+(?:/[a-z0-9]+)?|/", text))


def _has(key, title):
    return re.search(KEYWORDS[key], title) is not None


def variant_spec(variant, siblings):
    """Required / forbidden keywords for one catalog variant.

    Returns (spec, status): status OK, UNCERTAIN (computed, not published) or
    SKIP (not a regular traded TCG print, e.g. World Championship decks).
    """
    vtype = str(variant.get("type") or "").lower()
    foil = str(variant.get("foil") or "").lower()
    stamps = [_stamp(s) for s in (variant.get("stamps") or [])]
    sub = _sub(variant.get("subtype"))
    status = "OK"
    if any(s not in KNOWN_STAMPS for s in stamps):
        return None, "SKIP"  # player names (World Championship decks) and unknown stamps
    if any(s in UNCERTAIN_STAMPS for s in stamps) or (sub not in PLAIN_SUBTYPES and sub not in SHADOWLESS):
        status = "UNCERTAIN"  # set logo, player rewards, copyright 1999-2000, misprints ...
    require, forbid = [], []
    pattern = FOIL_KEYS.get(foil)
    if foil and not pattern:
        return None, "SKIP"
    if pattern:
        require.append(pattern)
    forbid += [p for p in PATTERNS if p != pattern] + ["error"]
    if vtype == "reverse":
        require.append("reverse")
    elif vtype == "holo":
        forbid.append("reverse")
        plain_siblings = [s for s in siblings if str(s.get("type") or "").lower() == "normal"
                          and not s.get("foil")]
        if plain_siblings and not pattern:
            require.append("holo")  # same card also exists as non-holo
    elif vtype == "normal":
        forbid += ["reverse", "holo"]
    else:
        return None, "SKIP"
    first = any(s in ("1st-edition", "1-auflage") for s in stamps)
    (require if first else forbid).append("first")
    if sub in SHADOWLESS:
        require.append("shadowless")
    elif any(_sub(s.get("subtype")) in SHADOWLESS for s in siblings):
        forbid.append("shadowless")
    for key, words in (("staff", ("staff", "mitarbeiter")),
                       ("prerelease", ("pre-release", "prerelease", "vorveroffentlichung"))):
        (require if any(s in words for s in stamps) else forbid).append(key)
    if "set-logo" in stamps or "player-rewards-program" in stamps:
        require.append("stamp")
    elif any(any(_stamp(x) in ("set-logo", "player-rewards-program") for x in (s.get("stamps") or []))
             for s in siblings):
        forbid.append("stamp")
    return {"require": sorted(set(require)), "forbid": sorted(set(forbid) - set(require))}, status


def number_ok(title, number, total, set_words):
    """Printed number: '074/131' (or '74/131'); letter numbers ('SV030', 'TG05');
    without a printed total the number plus a set name word."""
    number = str(number or "").strip()
    m = re.fullmatch(r"([A-Za-z]*)0*([0-9]{1,4})([A-Za-z]?)", number)
    if not m:
        return False
    letters, digits, suffix = m.group(1).lower(), m.group(2), m.group(3).lower()
    if letters:
        return re.search(rf"\b{letters} ?0*{digits}{suffix}\b", title) is not None
    if total:
        return re.search(rf"\b0*{digits}{suffix} ?/ ?0*{int(total)}\b", title) is not None
    return (re.search(rf"(?<![/0-9])0*{digits}{suffix}(?![/0-9])", title) is not None
            and any(w in title.split() for w in set_words))


def name_ok(title, names):
    words = title.split()
    for name in names:
        tokens = [t for t in norm(name).split() if t not in ("the",)]
        if tokens and all(t in words for t in tokens):
            return True
    return False


def matches(title, *, language, names, number, total, set_words, spec, set_id=""):
    """names[0] is the card name in the card's language, names[1] (optional)
    the name in the other language."""
    t = norm(title)
    if EXCLUDE.search(t) or re.search(OTHER_LANG[language], t):
        return False
    if not re.search(LANG_WORDS[language], t):
        # No language word: only a name that exists in this language alone
        # ("Garados", not "Gyarados") proves the card language.
        own, other = names[0], (names[1] if len(names) > 1 else None)
        if not other or norm(own) == norm(other) or not name_ok(t, [own]) or name_ok(t, [other]):
            return False
    if REPRINT.search(t) and not str(set_id or "").startswith(REPRINT_SETS):
        return False
    if not name_ok(t, names) or not number_ok(t, number, total, set_words):
        return False
    if any(not _has(k, t) for k in spec["require"]):
        return False
    return not any(_has(k, t) for k in spec["forbid"])


def fallback_price(prices, minimum=3):
    """Median of all matching offers; None below `minimum` offers.

    Unlike Cardmarket (offers filtered to Near Mint) eBay has no reliable
    condition filter, so the cheapest offers are often damaged copies; the
    median of all matches is the robust middle."""
    prices = sorted(p for p in prices if p and p > 0)
    if len(prices) < minimum:
        return None
    mid = len(prices) // 2
    return prices[mid] if len(prices) % 2 else round((prices[mid - 1] + prices[mid]) / 2, 2)


def signature(variant):
    """What a listing title can express about a variant."""
    return (str(variant.get("type") or "").lower(), str(variant.get("foil") or "").lower(),
            tuple(sorted(_stamp(s) for s in (variant.get("stamps") or []))), _sub(variant.get("subtype")))
