# Cardyssey Cardmarket – offizieller Preisguide und Druckidentität

Stand: 2026-11-06

## Datenquellen und Preisbedeutung

- Offizieller Cardmarket-S3-Katalog: `products_singles_6.json` (Cardmarket-ID, Name, Erweiterung).
- Offizieller S3-Preisguide: `price_guide_6.json` mit `avg30`, `avg30-holo`, Trends und niedrigsten Aggregatwerten.
- **Wichtig:** Preisguide-Aggregate sind keine eigenen DE-/EN-NM-Preise; `avg30-holo` ist kein garantierter Reverse- oder Spezialdruckpreis.
- Kein HTML-Scraping und keine inoffizielle Drittanbieter-API für diesen Workflow nötig.
- Keine unbestätigten Varianten-ID-Zuordnungen in `tcg_price_cache` veröffentlichen.

## Automatischer Betrieb

- Sonntag 04:10: `scripts/refresh-cardmarket-official-weekly.py --apply --language both` aktualisiert **bereits gespeicherte, sichere** `CARDMARKET_OFFICIAL`-Preisdatensätze. Schutz gegen parallele Läufe über `flock`; nächster Check in 7 Tagen.
- Montag 05:10: `scripts/run-cardmarket-identity-weekly.py --apply` aktualisiert den öffentlichen Katalog, beide DE-/EN-Queues, die ID-Kandidaten und die Prüfaufträge. Pro Lauf ein `flock`-Lock und ein Timeout.
- Wichtig: Cron aktualisiert den technischen Workflow, aber er kann ohne zusätzliche Identitätsevidenz keine Sonderdrucke automatisch verifizieren.

## Manuelle Druckprüfung

- Admin-Seite: `/admin/cardmarket-review`
- API: `/api/admin/cardmarket-print-review` (berechtigter Admin via `priceMonitorAllowed`).
- Datenbank: `cardmarket_print_identity_review`, Migration `V58__cardmarket_print_identity_review.sql`.
- Status: `PENDING_REVIEW`, `CONFIRMED_PRINT`, `NO_MATCH`, `DEFERRED`.
- Auswahl ist nur für Produkt-IDs erlaubt, die im selben passenden Set kandidieren; Prüfer bestätigt **Set, Nummer, Sprache, Edition, Holo/Reverse und Sonderdruck**.
- Human-Entscheidungen überleben künftige Kandidaten-Synchronisierungen. Auswahl veröffentlicht **keinen** Preis.
- Anzeige enthält das Katalog-Kartenbild und produktbezogene `avg30`-/`avg30-holo`-Guide-Referenzen, ausdrücklich nicht als separate DE-/EN-NM-Preise.
- 33 nur anhand wiederholter Produkt-IDs abgeleitete EN-Sets sind explizit als `INFERRED_SET` markiert, nicht als bestätigt.

## Reproduzierbare Checks

- `python3 scripts/build-cardmarket-identity-worklist.py`
- `python3 scripts/sync-cardmarket-print-review.py` – schreibfreier Vorabcheck
- `python3 scripts/test_cardmarket_print_review_admin.py` – Testfall in echter DB, danach automatisch bereinigt
- `python3 scripts/run-cardmarket-identity-weekly.py` – aktualisiert Queues/Reports, aber kein Review-DB-Import
- `python3 scripts/run-cardmarket-identity-weekly.py --apply` – inklusive Review-DB-Staging

Reports unter `reports/cardmarket-identity-pipeline-latest.json`, `reports/cardmarket-identity-worklist-{de,en}.csv` und `reports/cardmarket-print-review-all.csv`.

## Grenzen

- Nur das Vorhandensein einer Produkt-ID im offiziellen Katalog ist **kein** exakter Druckidentitätsnachweis.
- Eine eindeutige Set-Kandidaten-ID ist noch kein sprachgefilterter NM-Preis.
- Einzelne Produkte können mehrere physische Druckvarianten oder Sprachen repräsentieren.
- `CARDMARKET_OFFICIAL`-Preis-Cache wird nur für explizit sichere vorhandene Zuordnungen aktualisiert; bestätigte Review-Entscheidungen sind zunächst unabhängige Evidenz.
- Automatische Vollabdeckung sämtlicher Varianten wäre ohne zusätzliche Quellenbelege fachlich falsch.
