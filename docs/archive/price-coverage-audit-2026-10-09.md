# Price coverage audit — 2026-10-09

## Findings from the live database and code

The old finalizer changed every remaining `NO_PRICE` row in five languages into
`NO_PUBLIC_PRICE`, claimed a complete provider/web pass without per-row evidence,
and deferred it for 90 days. Therefore zero active cases was not proof of coverage.

The refresh target query and admin monitor expand `catalog_cards_mirror.variants`.
Entries with an empty array never enter that price-case list. The read-only audit
now reports them separately, alongside missing cache rows and status counts.
Pocket/digital sets and languages outside DE/EN/JA/KO/ZH-CN/ZH-TW are excluded.

| Language | Empty variant entries | With same set/number variant-bearing entry | Without such entry |
|---|---:|---:|---:|
| JA | 13,024 | 1,728 | 11,296 |
| KO | 19,772 | 7 | 19,765 |
| ZH-TW | 7,229 | 291 | 6,938 |

These are catalogue entry counts, not verified counts of unique missing cards.
Same-number twins are review hints, not permission to merge or copy variants.
The simplified-Chinese catalogue contains only 48 entries, all CSMPiC, so its
price count must not be described as coverage of the complete Chinese market.

## Applied recovery

Two public retailer feeds, Players Club HK and Beehive, supplied **834** additional
in-stock, exact traditional-Chinese single-card offers. First batch: 577;
verified legacy-SKU batch: 257. Exactly 834 history records were inserted.

Matching requires the approved collection, exact set, numerator, denominator,
normalized Chinese card name, an eligible single catalogue variant, one unambiguous
retailer option, independent Chinese product metadata, a positive finite price,
and explicit availability. Wrong-set products inside a collection, special foil
suffixes, other editions, alternate names, zero prices, and sold-out references
are rejected. A truncated/failed provider response prevents the batch write.

These are **asking prices**, not completed sales or a verified European market
value. Each cache row records ASKING, original HKD price, source URL/product ID,
availability, observation time, dated HKD/EUR conversion and the existing
0.92 NM/base normalization convention. No shipping is included. Higher/lower
condition valuations continue to use the application's existing condition model.

The importer is dry-run by default. Its weekly workflow step runs before the
older sold-out-reference fallback, refreshes its own prices when due (including
a six-day scheduling tolerance), and has a hard 180-second process limit.

The blanket finalizer has been replaced by an explicit, dry-run-by-default repair.
Only the three exact legacy diagnostics are reopened. A total of 2,937 rows were
reopened after the first import, of which the second import resolved 257. All 27
explicit unreleased-promo holds remain unchanged. Previous diagnostics are
preserved and reopening does not forge a successful-price timestamp.

## Final live price-cache counts

| Language | PRICE_FOUND | NO_PRICE | Explicit NO_PUBLIC_PRICE hold |
|---|---:|---:|---:|
| DE | 31,248 | 26 | 0 |
| EN | 34,005 | 53 | 0 |
| JA | 13,706 | 2,275 | 27 |
| KO | 239 | 0 | 0 |
| ZH-CN | 44 | 4 | 0 |
| ZH-TW | 8,102 | 322 | 0 |

Total: 87,344 PRICE_FOUND; 2,680 unresolved variants; 27 explicit promo holds.
The existing PRICE_FOUND population includes guides, estimates and sold-out
references. This audit does not certify all historic price assignments.

## Validation

- 14 offline regression tests for matching, language metadata, foil/edition
  rejection, stock status, malformed prices and failed/incomplete pagination.
- PostgreSQL tests on connection-local temporary tables (all rolled back):
  atomic cache/history update, concurrent-write protection, SQL quote escaping,
  precise status repair, manual-hold preservation, and coverage counting.
- Both production batches reported zero provider errors and matched/applied
  counts of 577/577 and 257/257; database counts and history totals cross-checked.
- Weekly YAML parsed and referenced scripts checked; no Android/API compilation
  required because this block changes Python jobs and shared price data only.

Commands:

```sh
python3 scripts/test-price-coverage.py
python3 scripts/test-price-coverage-postgres.py
python3 scripts/audit-price-coverage.py
python3 scripts/resolve-zhtw-retailer-prices.py  # read-only preview
```

## Remaining work

Audit missing catalogue variants without inventing Normal/Holo identities; examine
Korean and simplified-Chinese source coverage; review the remaining 2,680 exact
variant cases and existing inferred/reference prices. The full catalogue coverage
report is printed in the weekly workflow; the admin UI still lists variant cases,
so its totals do not yet include entries without variants. User-facing coverage
counts need a subsequent coordinated Android/Web change.
