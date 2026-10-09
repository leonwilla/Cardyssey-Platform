# Japanese numbered promo recovery and condition-correct ranges (2026-10-09)

## Applied retail recovery

- Two exact, in-stock Japanese offers from Hareruya: SV-P-223 at JPY 850 (EUR 4.79 NM) and SV-P-231 at JPY 1000 (EUR 5.64 NM).
- Extended the existing weekly importer to numbered SV-P and M-P promos. Require exact title, printed number and both set identifiers, PROMO rarity, a single ordinary catalogue variant without extra stamps/subtypes/foil, condition A, one available retailer variant and independently confirmed JPY units.
- Added E1 to exact edition discovery and canonical numeric VS/web collection handles. Mixed/unmarked classic editions continue to be rejected.
- Recovered offers are asking prices, not completed sales. Original currency, offer URL, condition, FX provenance and history are retained.
- Pre-write backup: /home/tv/cardyssey-backups/price-round4-20261009T144258Z. Evidence: /tmp/cardyssey-round4-applied.json.
- Confirmed atomic repeat application writes zero additional cache/history rows.
- Both new prices are served by the Android API and Web pricing proxy with exact Japanese language/variant matches.
- Remaining known variants without a price: 2,640, plus 27 deliberate release holds. Catalogue variant gaps remain separately unresolved.

## Shared range correction

The API previously returned the condition-adjusted unit price beside a range in unadjusted base values. For example, SV-P-223 at Near Mint showed EUR 4.79 with a EUR 5.2109–5.2109 range. Historical range endpoints now use the same condition factor and cent rounding as the unit price, without changing stored history or percentage trends. This shared response serves Android and Web.

## Validation

- 37 Python matching/coverage regression tests pass, including five new promo tests for language, set/number/name, printing, stock and condition.
- Four transactional PostgreSQL scenarios pass; unchanged classic edition matching remains covered.
- Three Kotlin regression cases cover single-offer ranges across all conditions, historical ranges/rounding, missing history and unchanged percentage trends.
- Backend Gradle test/installDist passed using the offline dependency cache. Runtime rebuilt/deployed. Twelve live requests across Android API/Web proxy, two cards and Mint/Near Mint/Played confirm that the unit value and both range endpoints agree. Admin authorization/filter checks also pass.

## Evidence requiring later investigation

- MC-672 and MC-719 have available mirror offers; these are not substituted for the currently unpriced normal variants. MC-721 mirror offer is out of stock.
- The inspected SV8a Master Ball collection did not supply offers for energy numbers 185–187. This alone does not prove those variants do not exist; no variants were removed.
- Korean TCGBOX exposes explicit KRW and stock metadata, but condition and exact printing checks need a separate source integration before valuation imports.
