# Cardmarket: durable identity first, filtered prices on the same verified page

1. Weekly official product catalog plus price guide refresh. Rebuild DE/EN source queues and prioritize existing price availability. Feed is a fallback, **not** an identity proof.
2. `cardmarket-enrich-queue-hints.py` adds candidate Cardmarket ID and official English name only when a single product is in an independently cross-checked provider set. The hint is never a print-verified ID.
3. Default Windows scheduled collector mode `identity` processes **all variants**, including priced bulk, to associate IDs and canonical URLs. It attempts the official catalog name before localized-name/number search, waits for asynchronous Cardmarket search results, and validates actual `idProduct` on a product page. Known wrong set slugs are rejected. Unclear print/set IDs go to review; no forced choices.
4. Once a product page is validated, the same visit may collect language + NM + explicit foil/edition offers. Priced bulk can skip costly offer pagination; missing or premium/special prints do not.
5. Every 15–30 minutes, `import-cardmarket-mapping-safe.py` stages browser-verified ID/URL as `SOURCE_ONLY` or fills a URL for an existing human-confirmed exact print. No price is written by this importer. Human decisions remain protected.
6. `import-cardmarket-filtered-prices.py` publishes the complete active asking-offer median only if `price_source_routing` has a matching **human-confirmed exact print**, same product ID and no conflicting URL, fully enumerated offers, German or English language filter, NM condition and explicit reverse/edition filters. Price source is **asking median, not sold median**. Incomplete samples are not published.
7. Weekly refresh reuses saved IDs and URLs; unresolved cases receive categorized reasons. Do not promote `NO_EXACT_NUMBER_SEARCH_HIT` to a true negative if search results were still loading. Existing accepted prices stay present during mapping.

Current known Cardmarket set mismatch: the provider candidate `557708` for `base1-8` resolves to `Expansion-Pack/Machamp-EXP`, **not** `Base-Set/Machamp-V1-BS8`. Guard this until the set crosswalk is corrected; do not import it as a match.

## Expansion-list index (since 2026-11-24): product pages without search

Cardmarket's search page triggered almost all Cloudflare challenges (386 of 393 blocks, 19.–23.11.2026). Product URLs now come from Cardmarket's own expansion lists instead:

1. `Cardmarket-Expansion-Index.ps1` (Windows, in the existing Edge tab, same-origin fetch, 11 s gap, stops on any challenge) reads `/en/Pokemon/Expansions` once a month and then the list pages `/Products/Singles/<Expansion>?site=N`. Each tile shows the canonical URL, the printed number (`Staryu (SK 103)`) and the `idProduct` in the image path. A slug only counts as verified when the tiles on its first page belong to the planned official `idExpansion`.
2. `build-cardmarket-expansion-index-plan.py` plans the crawl: only expansions holding DE/EN variants that need a browser price (no price, or existing price >= 2 EUR; cheaper cards keep the official guide price).
3. `apply-cardmarket-expansion-index.py` writes `variant_class`, `index_status`, `index_product_id`, `index_product_url`, `index_candidate_urls` into `queue-de/en.csv` and `index-set-url-guards.json`.
   * Standard and 1st-edition/unlimited prints with a unique printed number in the main expansion get a direct URL. The list beats name-based catalog singletons and TCGdex IDs (Skyridge Staryu 103/104 were swapped there); such rows are `DIRECT_PRODUCT_URL_ID_CORRECTED` with `index_previous_id`.
   * Special prints (pattern foils, stamps, shadowless, ...), holo+normal variants of the same card and numbers found only in an "Additionals" expansion get `REVIEW_*` with candidate URLs. The collector records them for human review without any provider request.
4. The collector opens index URLs directly (`lookup_strategy=EXPANSION_INDEX_DIRECT_V1`) and still requires the live idProduct, printed number and set. At most `MaxSearchCasesPerBatch` (6) cases per batch may still use search.
5. Refresh by value: >= 20 EUR weekly, >= 5 EUR every two weeks, otherwise monthly. Launcher runs 60-case batches for 50 minutes; the routine pause between launches is 3 minutes.
6. Telegram block alerts are sent only if the challenge is still present after 15 minutes.

## Cloudflare-Freigabe (stündlich)

Messung 19.–24.11.2026: Die Schutzseite kommt fast genau **60 Minuten** nach der letzten Freigabe, egal wie viele Seiten (25 bis 100) in der Stunde geladen wurden. Das Cookie `cf_clearance` wird gespeichert (Ablaufdatum 1 Jahr), aber Cardmarket lässt die Freigabe serverseitig nach einer Stunde ablaufen. Längere Gültigkeit lässt sich nicht einstellen; Umgehen (Klick-Automatik, Captcha-Löser, Tarn-Browser, Proxys) machen wir bewusst nicht, auch wegen Sperrgefahr für das eingeloggte Konto.

Was der Scanner deshalb tut:
- **Ruhig warten:** Bei einer Schutzseite bis zu 120 s nichts tun (nur alle 5 s nachsehen). Oft besteht der Browser die Prüfung dann selbst.
- **Nicht gegen die Wand laufen:** Der Session-Check liest nur einen 16-stelligen Fingerabdruck von `cf_clearance` (kein Wert wird gespeichert). Nach einem Block startet der Watchdog erst wieder, wenn eine **neue** Freigabe da ist (oder nach 30 min wie früher).
- **Telegram nach 5 min** (statt 15): „Seite neu laden (F5) und Kästchen anklicken“. Geht auch aus der Ferne per Remote-Desktop-App.
- **Login bleibt über Neustarts:** Der Launcher setzt im Scanner-Profil „Vorherige Sitzung fortsetzen“, bevor er Edge startet (Sicherung `Preferences.cardyssey-backup`).
