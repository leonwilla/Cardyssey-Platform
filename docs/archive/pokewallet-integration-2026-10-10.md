# PokéWallet server access — 10 October 2026

Authenticated the supplied Free account successfully. Credential lives outside the
repository in /home/tv/.config/cardyssey/secrets/pokewallet-api-key (0600, parent 0700).
Existing .env, frontend and app contain no new key.

scripts/pokewallet-client.py supplies authenticated server-side JSON requests.
A locked persistent rolling ledger reserves a maximum of 90/hour and 900/day;
requests, including failures, count toward the budget. HTTP 429 pauses future
requests for an hour. Remote response bodies and secrets are not logged.
All four setup calls were entered into the ledger before enabling the client.

Live set inventory: 854 sets; provider language codes jap=462, eng=331, chn=60,
che=1. This is an inventory, not verified price coverage. The che record is named
30th Celebration - Simplified Chinese; it must not be interpreted as traditional
Chinese merely from the abbreviation. No ordinary Korean set inventory was found;
a search for Korean returned World Collection promo products, not general Korean
booster coverage. Localised image-language arrays do not identify priced languages.

Live probes: SV1V Japanese cards have TCGplayer market estimates and Cardmarket
guides; CBB3C entries have Cardmarket guides. These are aggregate prices, not
condition-specific live Near Mint offers. Numeric set ID, product/printing
identity, language, finish and provenance must be verified before importing.
scripts/resolve-pokewallet-ja-market-prices.py implements the Japanese price
adapter. It requires pinned official identity, an exact independent CardTrader
blueprint, matching TCGplayer product ID, Japanese provider set, printed number
and denominator, rarity and ordinary finish. It imports only positive aggregate
market prices with a provider timestamp no older than eight days. No price is
inferred from translated images or from Cardmarket-only records without product-ID
proof. Manual --missing-only mode retains all existing positive prices. Weekly
workflow includes the adapter with a 50-request cap and the shared free quota.

Request-limited reports explicitly indicate budget_limited; this does not mean
the whole catalogue was checked. The weekly job can refresh this source's existing
rows; other providers' already positive rows remain outside this adapter's targets.

The Japanese booster filters additionally accept M-series official set codes,
and the TCGCSV group prefix match now accepts case differences such as m1L.
All pinned official identity, rarity, denomination and exact product-ID guards
remain mandatory. Missing-only runs preserve existing positive prices.

## Live validation
Initial bounded production preview examined 1,223 verified official Japanese
targets across all eligible groups, used 43 authenticated API requests, and found
zero additional safely importable prices. This largely overlaps the existing
TCGCSV dataset. The empty batch was applied idempotently: zero variants, prices
or history rows changed. Access to the provider is working; no claim that this
provider closes all Asian coverage gaps is made.

Validation: 13 provider/client offline tests plus 13 existing round-13 tests pass;
9 PostgreSQL missing-only import/preservation cases pass. Kotlin test/installDist
passes. New backend runtime deployed; all 32 prior recovered API and all 32 Web
detail/price pairs pass. The baseline of 91,414 positive prices is unchanged.
Wholly unpriced catalogue entries remain 37566.
