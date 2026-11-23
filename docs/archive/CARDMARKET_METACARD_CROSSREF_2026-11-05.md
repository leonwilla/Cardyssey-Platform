# Cardmarket metacard cross-reference audit

A read-only run inspected all 1460 outstanding German physical variant entries against the official Cardmarket Pokemon single-product JSON catalogue (75105 products in the response).

There are eight TCGdex external direct Cardmarket variant IDs:

- Six direct IDs have the same `idMetacard` as an in-set candidate but a **different `idExpansion`**. They refer to the underlying card family, not the same printed set/variant. Do not use these IDs as automatic replacements.
- One direct ID is not present in the current official catalogue.
- One direct ID is present among the in-set candidates, but its German language, precise edition/foil/stamp and printed number still require confirmation.

The audit script `scripts/audit-cardmarket-catalog-crossrefs.py` generates full per-row CSV and summary JSON with no production DB writes. Run it with the 1460-row fallback JSON input and the local reports output directory. It uses the existing official product JSON feed client. The filtered Cardmarket listing trend remains unsuitable as a German/NM-only price without offer evidence.

28 tests covering catalogue cross-references, review prioritization and offer checks passed. Reports were copied to the Tiny Desktop folder `Cardyssey-Cardmarket-Pruefung`.
