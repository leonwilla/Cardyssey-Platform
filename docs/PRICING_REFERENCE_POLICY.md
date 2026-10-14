# Cardyssey pricing: verified market values versus references

- `tcg_price_cache` with `PRICE_FOUND` supplies authoritative condition-scaled collection valuations.
- `price_reference_candidates` is **informational only**: no source from this table is added to `unitEur`, `marketUnitEur`, `valuedUnitEur` or `positionValueEur`.
- The backend explicitly exposes `referenceUnitEur`, `referenceUpdatedAtMs`, `referenceSource`, `referenceNote` on collection GET, and `referenceEur` plus note on missing TCG price quotes.
- English card-level API quotes remain unverified for special prints and condition. German matched-ID comparators are **English prices, not German valuations**.
- References appear in web collection, item editor, and Android collection with warning labels. They are not summed into portfolio totals or applied to marketplace sale prices.
- Only a valid, exact physical variant in an active collection may be manually marked verified in Admin Price Monitoring. Admin must explicitly confirm language, edition, stamp/size, condition and submit an HTTPS source. Entered price is normalized to the Mint basis for condition scaling.
- Manual changes preserve a full audit trail (`price_manual_review_audit`), record a `tcg_price_history` event, and must never overwrite an existing `PRICE_FOUND` cache row.
- The Admin review queue prioritizes variants currently held by users and retains query steps, candidate identities, provider results and reasons for uncertainty.
- Scheduled weekly reference polling uses only previously staged English card IDs, no paid API, with a low request rate. Failed provider calls leave previous references unchanged; age derives from provider `as_of`, not execution time.

Safety principle: a related product page, a general name-match, an unfiltered Cardmarket trend, or graded/wrong-condition sales can justify a **labeled reference**, but never by itself an exact condition/printing market value.
