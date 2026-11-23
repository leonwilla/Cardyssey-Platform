# Price recovery round 6 — 2026-10-09

## Result

Hardened the western leftover importer and added a read-only catalogue identity
review. No new prices or variants were imported in this round. The live guarded
apply changed zero cache rows and inserted zero history rows.

Ten English leftovers were examined: six have an exact ordinary-print blueprint
but no eligible marketplace offer or exact TCGplayer market statistic. Two are
special/oversized catalogue variants; two lack an explicitly matching printing.
The Raichu BW78 provider blueprint explicitly says Holo Promo whereas the open
catalogue variant is Normal. Mewtwo MEP104 has an unlabelled blueprint version,
which cannot establish the holo printing by itself.

## Import safeguards

- Importing the Python module performs no network/database access.
- Preview is the default; writes require --apply.
- Require exact expansion, Pokemon card category, collector number, native
  English name and explicitly labelled Non-Holo or Holo printing.
- Reject ambiguous blueprints, special editions, oversized/stamped variants.
- Marketplace offers require explicit English, Mint/Near Mint, ungraded,
  unsigned, unaltered, positive stock, one-card bundle and integer EUR cents.
- Remove played-condition and cross-condition inference.
- TCGplayer fallback requires exact product and printing, unique marketPrice,
  and verified positive USD/EUR rate. No midPrice substitution.
- Price writes compare the original cache timestamp and current catalogue
  set/number/name/image/full variant. Existing resolved/newer prices survive.
- Insert history only from changed cache rows. A repeated write creates no
  additional price or history rows.

All quotes retain the existing NM/base EUR convention. CardTrader quotes are
asking prices; TCGplayer marketPrice is a provider statistic, not a verified
individual completed sale.

## Catalogue review

The read-only report compares missing-variant official entries with same-language
provider entries sharing a set and zero-normalized collector number. It neither
copies variants nor changes prices. Different image hosts and distinct printings
can legitimately produce different image URLs.

| Language | Names differ, same image | Names and images differ | Same name, image differs |
| --- | ---: | ---: | ---: |
| ja | 51 | 16 | 1,402 |
| ko | 7 | 0 | 0 |
| zh-tw | 0 | 3 | 288 |

These are candidate pair counts and review hints, not confirmed erroneous cards.
For example, M6-098 and its official number twin disagree on the native name;
M6-099 additionally disagrees on the image. These conflicts require independent
print verification before correcting a name, transferring prices or variants.

Weekly refresh now runs the hardened importer explicitly with --apply, bounded
by 180 seconds. It preserves its evidence and a bounded catalogue review report
alongside the Asian retail evidence for 14 days. Reports list at most 100 detailed
conflict samples and aggregate all candidates by language and reason.

## Validation

- 58 offline price safety tests passed across five suites.
- Nine PostgreSQL rollback scenarios passed: success, repeated application,
  newer resolved price, changed number, variant, timestamp, image or legacy
  printing, and deleted target.
- Catalogue SQL fixture passed: whitespace-only name differences are ignored;
  cross-language and digital card matches are excluded; the three review
  categories are kept separate; no automatic repairs.
- Live preview and guarded apply agree: candidates 10, resolved identities 6,
  matched prices 0, applied prices/history 0.
- Existing exact catalogue twin preview: 254 verified pairs, zero missing
  variant entries eligible for another automatic recovery.
- Full physical price coverage audit rerun; no changes to coverage.
- git diff --check passed.

No API or Web runtime code changed, so no backend rebuild/deployment is required.

## Evidence on Tiny

- /tmp/cardyssey-round6-western-preview.json
- /tmp/cardyssey-round6-western-applied.json
- /tmp/cardyssey-round6-catalog-conflicts.json
- /tmp/cardyssey-round6-audit.json

Remaining work: independently resolve the conflicting native identities and
separate genuine print differences from image-host differences. Ordinary prices
must never stand in for rare editions or catalogue entries with unknown variants.
