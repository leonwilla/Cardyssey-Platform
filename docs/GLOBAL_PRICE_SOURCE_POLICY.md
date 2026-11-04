# Cardyssey – globale Preisquellenstrategie (Stand 04.11.2026)

## Geltungsbereich und tatsächlicher Rollout

**Aktiv für alle bereits katalogisierten Sets der Sprachen DE, EN, JA, KO, ZH-CN und ZH-TW.**
Die zentrale DB-Tabelle `global_price_source_policy` umfasst *jede Katalogkarte*, auch
Karten ohne identifizierbare Druckvariante (`__NO_EXACT_PRINT__`). Entscheidend ist
immer die Kombination **Sprache + Set + Karten-ID + physische Druckvarianten-ID**.
Das Verhalten gilt in der zentralen `GET /api/v1/pricing/cards/{id}`-API für Android
und Web. Die bisherige manuelle Auswahl `market=TCG|EBAY` funktioniert weiter;
neues `market=AUTO` wird bei fehlender Marktangabe verwendet. Die Preis-API
erfindet keine Werte aus anderen Sprachen und wechselt bei Bulk nicht auf eBay.

**Achtung:** Eine globale Quellenentscheidung ist nicht gleichbedeutend mit einer
erfolgreichen Preisbeschaffung! Kein massenhafter Preisimport wurde vorgetäuscht.
Nur der bestehende deutsche eBay-Collector für die bislang eingerichteten fünf
Sets ist produktiv automatisiert. Andere DE/EN-Sets sind jetzt entsprechend
klassifiziert, aber **nicht** automatisch alle für eBay-Scraping eingeplant.
Wegen eBays Zugriffsbeschränkungen geschieht das nicht in 163 parallelen Jobs.
Für JA/KO/ZH-CN/ZH-TW gibt es keinen neuen eBay-Scraper; dort wird die
lokale/regionale TCG-Preisstrecke genutzt. Der zentrale Cache-Worker aktualisiert
weiterhin die TCG-Preisquellen gemäß seinen bestehenden Limits/Zeitfenstern.

## Regeln

| Kartenklasse | Quellenstrategie | eBay |
|---|---|---|
| Häufig / Ungewöhnlich / Common / Uncommon | Sprach- und druckvariantenpassende TCG- bzw. regionale Marktwerte | Nicht für automatische eBay-Setläufe; explizite Admin-Einzeltests bleiben möglich |
| Selten / Holo / Illustration / Ultra / EX / Promo | DE/EN: nachgewiesene eBay-Verkäufe, sonst passende TCG-Referenz. Asien: regionale Märkte | Vorhandene DE-Collector-Jobs; keine globale aggressive Abfrage |
| Seltenheit fehlt | `RARITY_UNVERIFIED`, keine automatische Bulk-Einstufung | Separate Prüfliste |
| Physische Druckvariante fehlt | `NO_EXACT_VARIANT`, kein erfundener Variantpreis | Druckidentität nacharbeiten |

**Providerpriorität:**
- DE: direkte Cardmarket-Quellen → TCGdex/Cardmarket-Referenzen; keine
  implizite amerikanische TCGplayer-Zuordnung.
- EN: Cardmarket/TCGdex → eindeutig zugeordnete TCGplayer-Quellen.
- JA: japanische Händler (`WEB_*_JP`), japanische CardTrader-Varianten,
  expliziter `TCGCSV_JP_MARKET`, danach exakt lokalisierte CardTrader-Angebote.
- KO: koreanische Händler (`WEB_*_KO`) und `CARDTRADER_KO*`.
- ZH-TW: Hongkong-/Taiwan-Händler (`WEB_*_HK`) und exakt
  sprachkodierte CardTrader-Einträge.
- ZH-CN: nur exakt sprachkodierte CardTrader-Einträge, solange keine andere
  geprüfte chinesische Quelle eingerichtet ist.

Nicht regionalspezifisch verifizierte TCGdex-Werte in den asiatischen Sprachen
werden **nicht** automatisch als lokale Marktpreise freigegeben. PriceCharting
ist in keiner der Bulk-Prioritäten enthalten. Eine fehlende Quelle ist ein
sichtbarer `MISSING_LOCAL_PRICE`-Status, nicht `0 €` und kein falscher
Fremdwährungspreis.

## Bestand und tatsächliche Lücken

Maschinenlesbarer Stand: `docs/global-price-source-coverage.json`.
Er enthält pro Sprache die Zahl der Katalogkarten, Sets, Varianten bzw.
Platzhalter, Bulk-Prints mit/ohne Preis, fehlende Seltenheiten und fehlende
Druckidentitäten. Das Live-Monitoring erreicht die Werte über das geschützte
`GET /api/admin/price-source-coverage`.

**Offene Arbeit:** Lokale Preisquellen für KO, ZH-TW und ZH-CN vervollständigen;
für JA/KO/ZH-TW fehlende Seltenheiten und physische Varianten rekonstruieren;
regionale Quellen auf richtige Sprache, Ausgabe, Foil/Reverse und Zustand prüfen;
DE/EN-eBay-Suche bei Bedarf vorsichtig auf weitere Rare-Sets erweitern.
Eine fehlende Quelle wird weder als `PRICE_FOUND` noch als eBay-Verkauf gebucht.
Historische Verkäufe werden bei Änderungen der Quellenstrategie nicht gelöscht.

## Technische Umsetzung

- `V55__global_price_source_policy.sql`: persistente Quelle pro Sprache,
  Katalogkarte und Druckvariante; `global_price_policy_sync`: Auditstatus.
- `scripts/sync_global_price_source_policy.py`: idempotenter Upsert aus
  `catalog_cards_mirror` + `tcg_price_cache`, keine externen Anfragen und keine
  Preisänderungen. Aktualisiert auch fehlende Karten-/Druckdaten.
- `GlobalPriceSourcePolicy.kt` und `PricingRoutes.kt`: gemeinsame API-Regel;
  `market=AUTO`, `market=TCG`, `market=EBAY`; Antwortfelder `policyClass`,
  `policyStatus`, `policyProviderFamily`, `preferredMarket`.
- `scripts/price_monitor_catalog.py`: TCG-Monitor liest dieselbe exakte
  Druck-/Sprachquellenentscheidung; keine beliebige jüngste Fremdvariante.
- `cardyssey-global-source-policy.timer`: täglich 04:45 Uhr Europe/Berlin
  mit geringer zufälliger Verzögerung, systemd user service auf dem Tiny.

**Betrieb/Prüfung:**

```bash
python3 /home/tv/cardshop/scripts/sync_global_price_source_policy.py
python3 -m unittest /home/tv/cardshop/scripts/test_global_price_source_policy.py -q
systemctl --user status cardyssey-global-source-policy.timer
journalctl --user -u cardyssey-global-source-policy.service --no-pager -n 40
```

Dies ist eine Routing-/Qualitätssicherungsumstellung. Noch offene Datenlücken
werden sichtbar und sind **keine** stillschweigend abgeschlossenen Preise.
