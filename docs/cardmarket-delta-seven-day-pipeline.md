# Cardmarket DE/EN – sicheres 7-Tage-Delta-Gate (11.11.2026)

## Ziel und bestehender Zeitplan

- Kostenloser offizieller S3-Produktkatalog und Preisguide (Pokémon Game-ID 6).
- Automatische Identitäts-/Queue-Aktualisierung: **Montag 05:10 Uhr** über den
  vorhandenen Tiny-Crontab mit `flock` und `timeout`.
- Den laufenden Windows-Scanner **nicht stoppen**, keine Laufzeit-/Session-Sperren umgehen.
- Request-Limits bleiben: 10 Sekunden Mindestpause, 16 Karten pro Sprachbatch,
  45 Minuten nach regulären Batches und 4 Stunden nach `BLOCKED`.

## 1. Sicheres S3-Delta-Gate

Die Wochenroutine erzeugt die vollständigen DE-/EN-Queues weiterhin aus dem
Katalog und der Datenbank. `prioritize-cardmarket-scan-queue.py` setzt zunächst
`delta_browser_skip=NO` und lässt fehlende Preise, Sonderdrucke und High-Value
(>=15 EUR) in der Scanpriorität.

Danach vergleicht `cardmarket_delta_scan.py` je Produkt `avg30` **und**
`trend` mit der vorherigen gespeicherten vollständigen Guide-Version.
Ein Browser-Skip ist nur möglich, wenn **alle** Bedingungen erfüllt sind:

1. DE oder EN mit eigener bestätigter Cardmarket-Produkt-ID,
   `VERIFIED_PRODUCT_ID` und `cardmarket_print_identity_review.CONFIRMED_PRINT`
   auf genau derselben Cardyssey-Varianten-ID.
2. Eine normale Karte ohne Folie/Sonderdruck/Stempel, keine manuelle
   Nachprüfung, bereits bestehender `PRICE_FOUND` zwischen 0 und <15 EUR.
3. Neuester Browserbeleg aus derselben Sprache, derselben Produkt-ID,
   Login `AUTHENTICATED`, vollständige gefilterte Angebotsliste,
   mindestens ein tatsächlich passendes NM-Angebot, keine Pagination-Fehler,
   Alter **unter 28 Tage**.
4. Ein **neuer**, nicht veralteter S3-Preisguide; die früher gespeicherte
   Vergleichsversion ist nicht älter als 28 Tage und beide Werte liegen vor.
   Die Toleranz wird anhand des letzten **bestätigten DE-/EN-Preises** gestaffelt:
   - Unter **5,00 €** müssen Änderungen bei `avg30` **und** `trend` jeweils
     strikt **unter 10 %** liegen.
   - **5,00–14,99 €**: Änderungen bei **beiden** Guide-Werten müssen
     gleichzeitig strikt **unter 3 % UND unter 0,30 €** bleiben.
     Beispiel: **12,00 € → 11,50 €** erzwingt einen Browser-Scan.
   - Ab **15,00 €**: niemals Delta-Skip.
   Die Schwellen sind strikt: exakt 10 %, 3 % oder 0,30 € reichen nicht
   für einen Skip. Bei unklaren/mangelnden Belegen wird immer gescannt.

Sind alle Nachweise erfüllt, setzt das Gate `needs_price=NO`,
`delta_browser_skip=YES` und einen expliziten Begründungscode.
Es wird **kein Artikel entfernt**. Die restlichen Fälle bleiben in der
Browser-Queue. Die separate Datei
`cardmarket-guide-delta-state.json` speichert den letzten Vergleichsstand.

**Wichtig: Eine Guide-Kontrolle ist keine DE-/EN-/NM-Preisverifizierung.**
Daher schreibt dieses Gate bewusst **nicht** in
`tcg_price_cache.updated_at`, `next_attempt_at`,
`tcg_price_history` oder die veröffentlichte Sammlungspreisquelle.
Andernfalls würde die Anwendung einen alten sprachspezifischen Preis
fälschlich als frisch überprüft anzeigen. Der Guide-Check hat seinen eigenen
Nachweis im Delta-State/CSV und im Admin-Monitoring. Diese Abweichung vom
ursprünglichen Vorschlag ist eine notwendige Fail-Closed-Schutzmaßnahme.

Beim **ersten Lauf** fehlt noch ein früherer Guide-Stand: der Lauf legt die
Baseline an; er kann folgerichtig noch keine Karte wegen geringer Änderung
ausschließen. Ebenfalls werden Karten ohne `avg30` und `trend` nie rein
auf Schätzwerte hin übersprungen. Die tatsächliche Einsparung muss aus
künftigen Freigaben/Beobachtungen gemessen werden; 80 % sind **kein**
garantierter Wert und aktuell wegen weniger bestätigt zugeordneter Varianten
nicht erreichbar.

## 2. Browser-Optimierung

`cardmarket-language-browser-collector.ps1` verwendet bei geeigneten
normalen/reversen Karten bereits für die **erste** Produktnavigation die durch
`New-CardmarketOfferFilterUrl` erzeugte sprachspezifische URL.
Anschließend werden weiterhin **live** Produkt-ID, Kartennummer,
Anmeldung sowie alle Filterfelder im DOM kontrolliert.

- Bei nicht übereinstimmenden Filterfeldern: sicherer Formular-Fallback.
- Bei Cloudflare/403/429: pausieren, kein Umgehungsversuch.
- Maximal **3** AJAX-`loadMore`-Seiten pro Karte.
- Bei mehr verfügbaren Angeboten bleibt
  `all_pages_complete=false`, `median_all_offers_eur=null` und
  `FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE`.
  Nur tatsächlich vollständige, filterkonforme Angebotslisten können einen
  Vollmarktmedian erhalten; dreiseitige Teilauszüge sind nur Diagnosewerte.
- V1/V2/Pokéball/Meisterball/Stempel ohne exakte Bestätigung: **kein Preis**.

## 3. Spielprofile für spätere andere TCGs

`config/cardmarket-game-profile.json` enthält die verifizierte Pokémon
Game-ID, den Pfad `/Pokemon/` und die beiden S3-Dateinamen. Python lädt diese
über `cardmarket_game_profile.py`, PowerShell über
`cardmarket-game-profile.ps1`. Die aktive Pipeline verwendet ausschließlich
das validierte Profil `pokemon` (Game-ID 6).

**One Piece/Magic sind vorbereitet, aber noch nicht freigegeben.** Für jedes
neue Spiel müssen die offiziellen Game-/Expansions-IDs, Set-Crosswalks,
Varianten- und Zustandslogik zuerst unabhängig geprüft werden. Nur die
Profilkonfiguration anzulegen erlaubt noch keinen Preisimport anderer TCGs.

## Ausführung, Betrieb und Tests

```bash
python3 -m unittest discover -s scripts/cardmarket/tests -q
python3 scripts/cardmarket/core/cardmarket_delta_scan.py                # DRY_RUN, keine Queue-Änderung
python3 scripts/cardmarket/core/run-cardmarket-identity-weekly.py --apply  # NICHT während aktivem Scanner
```

- Eigene Tests: `scripts/cardmarket/tests/test_cardmarket_delta_scan.py` (Guide-Grenzwerte,
  Erstlauf, Sprache, Druckmerkmale, Alter, bestätigt/nicht bestätigt,
  15-EUR-Grenze, fehlende Werte, Queue-Erhaltung, keine Preisänderungen).
- Vor produktivem Queue-Neuschreiben wird ein jüngst als `RUNNING`
  protokollierter Scanner geprüft. Bei Aktivität wird abgebrochen.
- Den laufenden Windows-Scan nicht stoppen und die bestehenden Queue-Dateien
  nicht manuell ersetzen. Änderungen am Browser-Code greifen erst bei einem
  **späteren natürlichen Prozessstart**.
- Die Admin-Anzeige unterscheidet die Zahl der wegen stabilen Guides
  übersprungenen Browseraufrufe ausdrücklich von frisch bestätigten Preisen.
