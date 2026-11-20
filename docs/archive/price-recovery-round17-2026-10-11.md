# Price recovery round 17 — 2026-10-11

Added **243** first-price Japanese catalogue entries after checking all **1663** eligible unpriced identities. No arbitrary card limit was used. The new source scopes produced 243 in-stock candidates; all 243 passed live verification with no provider errors.

## Results

- Hareruya: 170 new prices.
- TorecaCamp: 73 new prices.
- Entirely unpriced catalogue entries remaining: **34,486**.
- German: 0; English: 15; Japanese: 9,793; Korean: 17,164; Simplified Chinese: 4; Traditional Chinese: 7,510.

These counts use the existing coverage audit's catalogue-entry definition, including duplicate records, rather than counting cache variants or deduplicated physical cards.

## Scope extension

The pinned Japanese identity loader now includes numbered modern Mega sets and an explicit allowlist of observed Mega deck codes: MA, MBD, MBG, MDB, MEE, MEM, MEZ, MG, MMB-P, MMB-S and MP1. Unsupported M-prefixed names and older BW/XY boosters remain held. Raw record, source revision, official URL/hash ID, set/number/denominator, complete native name, image and catalogue identity uniqueness must still agree. Missing official rarity remains missing.

The Hareruya reader now reads its publicly linked mega collection when eligible Mega targets exist, alongside SV, Sword/Shield, Sun/Moon and the previously enabled numbered XY promo scope. TorecaCamp retains observed explicit promo collection handles. Complete inventories contained 21,643 Hareruya records and 3,927 TorecaCamp records for the current target scopes. The same strict condition-A, unit quantity, JPY currency, exact live product/SKU, stock and asking-reference guards from round 16 remain in force.

Updated weekly reader code automatically covers the added Mega scope. API and catalogue-import marker support was already deployed in round 16; no new backend or web changes were needed.

## Sunday refresh and preservation

This manual run took place during the authorized Sunday 04:17–24:00 UTC API refresh lane. An early snapshot comparison detected existing TCGdex-family cache updates **before any manual import**, attributable to that weekly worker. Those authorized weekly changes were not reverted.

The manual import used a short database transaction with a writer lock on the cache, a transaction-local snapshot of all existing positive rows, existing missing-only and catalogue identity guards, per-source expected import counts, and a before/after comparison of every original positive card/language/variant/source/amount/timestamp. The transaction confirmed all **94,282** previously positive rows were unchanged by the manual operation. Concurrent read-only API requests remained available; automatic writers resumed after commit. No existing positive price was selected for manual provider work or rewritten by this import.

Import replay wrote zero variants, prices and history points. Each of the 243 new database prices was checked against its verified source and exact amount. API/Web checks passed for 42 representatives covering every source/set/missing-rarity cohort and price extremes, including exact language/variant, source, converted EUR, bounds and generated variant.

## Traditional Chinese source review

Read all **6,029** products from CardLand's public Traditional Chinese single-card category (61 pages), including **5,254** products marked in stock. Pagination repetition and completeness were checked. Four products contained explicit condition text, and those described Deck-grade cards rather than establishing NM. The remaining inspected feed records did not provide a usable NM/default-condition contract. Source-guidance searches did not establish one either. No Chinese price or synthetic variant was created from an unproved condition.

This is a source-quality hold, not a claim that these cards have no prices anywhere. Product names, SKUs and categories can identify cards but cannot establish their condition. Existing prices were not audited or modified on this basis.

Primary source inventory: https://cardland.com.hk/wp-json/wc/store/v1/products?category=4999&per_page=100&page=1
Primary Japanese collection: https://www.hareruya2.com/collections/mega

## Validation and evidence

- 30 exact identity/source/currency/condition/inventory-scope tests passed, including three new Mega cases.
- Existing round-13 offline missing-only tests passed (13 cases).
- Actual manual import transaction, all-new-price verification, replay, API/Web verification and final coverage audit passed.
- Repository whitespace validation passed.
- Pricing backup: /home/tv/cardyssey-backups/price-round17-20261011/pricing.dump.
- Remote source and verification evidence: /tmp/cardyssey-round17-*.json and logs.

Newly priced entries by set:

| Set | New prices |
| --- | ---: |
| MA | 32 |
| MBD | 20 |
| MBG | 21 |
| MDB | 5 |
| MEE | 17 |
| MEM | 14 |
| MEZ | 16 |
| MP1 | 23 |
| S1W | 1 |
| S2a | 1 |
| SB | 1 |
| SD | 1 |
| SEF | 1 |
| SGG | 2 |
| SI | 7 |
| SMA | 6 |
| SMD | 1 |
| SMH | 2 |
| SMP | 10 |
| SN | 1 |
| SP1 | 1 |
| SVAW | 1 |
| SVD | 1 |
| SVJL | 1 |
| SVM | 1 |
| SVN | 1 |
| SVOD | 1 |
| XYP | 54 |
