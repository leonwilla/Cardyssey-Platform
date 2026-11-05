# Cardyssey – Preisquellen, Preisabdeckung und Rückbau (05.11.2026)

Datenquelle: **Live-Datenbank** `global_price_policy_sync.summary` (letzter Lauf `2026-11-05T03:48:42.804103+00:00`), abgerufen am 05.11.2026; Zählbasis `global_price_source_policy` mit **Sprache + Karte + exakte physische Druckvariante bzw. Platzhalter**. Ein Preis-Snapshot ist nicht dasselbe wie ein heute live neu abgerufener Preis. Die separate eBay-Historie ist nicht in dieser Quellensummen-Tabelle enthalten. Einige TCGdex-Einträge sind geteilte oder Katalogpreise; Abdeckung bedeutet deshalb *vorhandener passender Policy-Preis*, nicht für jede Variante unabhängig verifizierter aktueller Handel.

## Gesamtbestand

- **134,295** Druckvarianten/Platzhalter, **73,893** mit Preis (55.0 %), **60,402** ohne passenden Preis (45.0 %).
- **1121 Sprach-/Set-Kombinationen**; dieselbe Edition in mehreren Sprachen zählt mehrfach.
- Keine PriceCharting-Werte im `global_price_source_policy`-Routing; `tcg_price_cache` hat beim Rückbau **0** PriceCharting-Quellenwerte.

| Sprache | Sets | Prints | Mit Preis | Ohne Preis | Abdeckung | Bulk-Preisabdeckung |
|---|---:|---:|---:|---:|---:|---:|
| Deutsch (`de`) | 163 | 32.553 | 29.223 | 3.330 | 89.8 % | 17.048/18.728 (91.0 %) |
| Englisch (`en`) | 216 | 36.545 | 33.570 | 2.975 | 91.9 % | 19.232/20.851 (92.2 %) |
| Japanisch (`ja`) | 343 | 29.485 | 7.449 | 22.036 | 25.3 % | 3.000/11.147 (26.9 %) |
| Koreanisch (`ko`) | 262 | 20.011 | 2.671 | 17.340 | 13.3 % | 1.621/7.517 (21.6 %) |
| Chinesisch vereinfacht (`zh-cn`) | 1 | 48 | 14 | 34 | 29.2 % | nicht klassifiziert |
| Chinesisch traditionell (`zh-tw`) | 136 | 15.653 | 966 | 14.687 | 6.2 % | 108/2.569 (4.2 %) |

## Quellen und Lücken je Sprache

### Deutsch (`de`)

**Zuständige Wege:** TCGdex (Cardmarket-nahe Referenz- und Katalogwerte), ergänzend direkte Cardmarket-Daten; eBay-Verkäufe für geprüfte seltene Karten (separater Verkaufspreisweg).

**Im aktuellen Quellen-Snapshot:** `TCGDEX` 19.112, `TCGDEX_CATALOG` 7.980, `TCGDEX_SHARED` 1.543, `TCGDEX_FAMILY` 520, `TCGDEX_CATALOG_CACHE` 40, `CARDMARKET_OFFICIAL` 14, `CARDMARKET_WEB` 5, `TCGDEX_SHARED_HOLO` 5, `CARDMARKET_DE_NM_WEB` 3, `CARDMARKET_OFFICIAL_CT_IDENTITY` 1.

**Fehlende Daten:** 3.330 Prints ohne Preis; 284 unbekannte Seltenheiten. Priorität: bestehende Cardmarket-/TCGdex-Quellen und Rare-eBay-Varianten exakt zuordnen.

### Englisch (`en`)

**Zuständige Wege:** TCGdex, TCGCSV/TCGplayer, PokémonTCG.io und einzelne direkte Cardmarket-Quellen; geprüfte seltene Karten können eBay-Verkaufspreise verwenden.

**Im aktuellen Quellen-Snapshot:** `TCGDEX` 20.583, `TCGDEX_CATALOG` 8.631, `TCGDEX_SHARED` 1.630, `TCGCSV_TCGPLAYER` 1.416, `POKEMONTCGIO_CARDMARKET` 546, `TCGDEX_FAMILY` 523, `POKEMONTCGIO_TCGPLAYER` 159, `CARDMARKET_OFFICIAL` 41, `TCGDEX_CATALOG_CACHE` 22, `CARDMARKET_OFFICIAL_CT_IDENTITY` 12, `TCGDEX_SHARED_HOLO` 5, `TCGCSV_TCGPLAYER_NAMED_SPECIAL` 2.

**Fehlende Daten:** 2.975 Prints ohne Preis; 645 unbekannte Seltenheiten. Priorität: fehlende TCGCSV/TCGplayer-IDs und Special/Reverse/Foil-Sonderformen abgleichen.

### Japanisch (`ja`)

**Zuständige Wege:** Japanische Händler (Hareruya, TorecaCamp, CardRush), lokale CardTrader-Angebote sowie einzelne explizit regionale TCGCSV-Werte.

**Im aktuellen Quellen-Snapshot:** `WEB_HARERUYA_JP` 2.198, `CARDTRADER_MARKETPLACE` 2.114, `WEB_TORECACAMP_JP` 1.888, `CARDTRADER_JP_NM` 931, `CARDTRADER_SP_INFERRED` 149, `CARDTRADER_EDITION_INFERRED` 80, `TCGCSV_JP_MARKET` 29, `WEB_CARDRUSH_JP` 23, `CARDTRADER_MP_INFERRED` 18, `CARDTRADER_PLAYED_INFERRED` 10, `CARDTRADER_EDITION_INFERRED_PCG` 9.

**Fehlende Daten:** 22.036 Prints ohne Preis; 7.766 ohne exakte Druckvariante, 11.453 unbekannte Seltenheiten. Zuerst Druckidentität, Seltenheit und regionale Händlerzuordnung verbessern.

### Koreanisch (`ko`)

**Zuständige Wege:** CardTrader für exakt koreanische Karten sowie lokale koreanische Shops (u.a. Uturi, Mana, Nero, Lake).

**Im aktuellen Quellen-Snapshot:** `CARDTRADER_KO_NM` 2.335, `WEB_UTURI_KO` 159, `WEB_MANA_KO` 49, `WEB_NERO_KO` 38, `WEB_MEWTWO_KO` 28, `WEB_LAKE_KO` 21, `WEB_LEVELUP_KO` 19, `WEB_BLACKROSE_KO` 13, `WEB_SHINY_KO` 8, `WEB_UNICORN_KO` 1.

**Fehlende Daten:** 17.340 Prints ohne Preis; 7.497 ohne exakte Druckvariante, 7.555 unbekannte Seltenheiten. Zuerst physische Varianten aus Katalog und lokale Marktwerte verbessern.

### Chinesisch vereinfacht (`zh-cn`)

**Zuständige Wege:** Ausschließlich sprachgenau zugeordnete CardTrader-Preise; kein allgemeiner chinesischer Händlerimport.

**Im aktuellen Quellen-Snapshot:** `CARDTRADER_MARKETPLACE` 14.

**Fehlende Daten:** 34 von 48 Prints ohne Preis; alle 48 ohne bestätigte Seltenheit. Nur ein Set katalogisiert: Katalogumfang und lokale Quellen erweitern.

### Chinesisch traditionell (`zh-tw`)

**Zuständige Wege:** Hongkong-Quellen (Beehive, PlayersClub, Cardland) und sprachgenau zugeordnete CardTrader-Preise.

**Im aktuellen Quellen-Snapshot:** `WEB_BEEHIVE_HK` 525, `WEB_PLAYERSCLUB_HK` 299, `CARDTRADER_MARKETPLACE` 97, `WEB_CARDLAND_HK` 45.

**Fehlende Daten:** 14.687 Prints ohne Preis; 7.229 ohne exakte Druckvariante, 11.986 unbekannte Seltenheiten. Händler-/Variantenzuordnungen aus HK/TW und Seltenheiten verbessern.


## Source-Routing: was die Preise liefert

- **DE:** TCGdex-gestützte Referenzdaten/TCG-Caches, einzelne Cardmarket-Feeds bzw. manuelle bestätigte Cardmarket-Quellen. Der deutsche eBay-Collector ist ein gesonderter *verkaufte Artikel*-Kanal für Rare-Karten, nicht Teil der normalen Bulk-Preisquelle.
- **EN:** TCGdex plus explizit passende TCGplayer-Werte über TCGCSV oder PokémonTCG.io; Cardmarket als Ergänzung. eBay-Verkäufe analog für seltene deutsche/englische Karten bei vorhandenen Nachweisen.
- **JA:** lokale JP-Händler und japanische CardTrader-Angebote; kein ungesicherter generischer EN-Preis als Ersatz.
- **KO:** CardTrader mit nachgewiesener koreanischer Identität und koreanische Händler.
- **ZH-CN:** nur sichere, exakt chinesische CardTrader-Werte; großer Katalog-/Quellenrückstand.
- **ZH-TW:** Hongkong-/Taiwan-Händler und passende CardTrader-Werte; nicht einfach Preise aus Japanisch oder Englisch übernehmen.
- **Nicht produktiv:** PriceCharting (kein lizenzierter API-Zugang und keine exakten Produkt-IDs), CapSolver (Schlüssel-Zugriff 401), Solverr (Cloudflare-Challenge nicht gelöst), zusätzliche unbekannte Gratis-Preis-APIs ohne kommerziell geprüften Datenvertrag.

## Rückbau – entfernt am 05.11.2026

1. Auf dem Tiny `/home/tv/.config/cardyssey/capsolver.key` gelöscht; keine lokale Kopie des Schlüssels bewusst behalten. **Empfehlung:** Schlüssel zusätzlich im CapSolver-Dashboard widerrufen, weil er vorher im Chat stand.
2. Git-Dateien gelöscht: `scripts/capsolver_preflight.py`, `scripts/setup_capsolver_key.py`, `scripts/test_capsolver_preflight.py`, `scripts/diagnose-pricecharting-access.py`, `scripts/test_diagnose_pricecharting_access.py`, `scripts/refresh-pricecharting-exact.py`, `scripts/prepare-pricecharting-review.py`, `config/pricecharting-exact-variants.csv` (enthielt ausschließlich Header), `docs/CAPSOLVER_FREE_TRIAL.md` und `docs/PRICECHARTING_CONNECTOR_STATUS.md`.
3. Optionale PriceCharting-API-Abfrage und dauerhafte PriceCharting-Suchhinweis-Anreicherung aus `.github/workflows/tcgcsv-price-refresh.yml` entfernt; PriceCharting-Sonden aus der manuellen `.github/workflows/scraper-connectivity-audit.yml` entfernt. Andere Provider-Jobs unangetastet.
4. PriceCharting-Temporärberichte unter `/tmp` entfernt. Der Testcontainer `cardyssey-test-solverr` und das Solverr-Image waren bereits beim vorherigen Experiment gelöscht und wurden erneut geprüft.
5. **Erhalten:** `docs/FREE_PRICE_SOURCE_EXPERIMENTS_2026-11-05.md` (Audit-Historie), dieser Bericht, alle live eingesetzten Cardmarket/TCG-/CardTrader/eBay-Skripte und Tabellen. Historische Daten bleiben erhalten; keine Datenbanktabellen oder regulären Preise gelöscht.

## Wiederherstellung oder erneuter Test

Die entfernten Projektdateien sind über die Git-Historie vor dem Rückbau wiederherstellbar. Eine neue PriceCharting-Integration sollte nur mit erlaubter kommerzieller Verwendung, einem separaten API-Secret und **exakten** Druckvariantenzuordnungen erfolgen. CapSolver/Browser-Experimente nicht unkontrolliert wiederholen.

## Nächste Prioritäten

1. **JA/KO/ZH-TW:** Druckvarianten und Seltenheiten aus vertrauenswürdigen Katalog-/Setdaten ergänzen (ohne Preiswerte zu erfinden); anschließend lokale Händler- und CardTrader-Preis-IDs zuordnen.
2. **DE/EN:** ca. 6.305 fehlende Prints gezielt über Cardmarket, TCGCSV/TCGplayer und echte eBay-Verkäufe sichten; Sondervarianten, Reverse und Promos präzisieren.
3. **ZH-CN:** Katalogabdeckung erweitern und erst dann flächendeckende regionale Preisquellen erschließen.
4. Überwachung: `python3 scripts/price_source_coverage.py`; Timer `cardyssey-global-source-policy.timer`, TCG-Refresh und eBay-Collector beibehalten. Keine automatische Fremdsprachen-Preisübernahme, keine Massen-Scraper an gesperrten Websites.
