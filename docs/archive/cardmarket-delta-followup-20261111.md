# Cardmarket Betrieb: Baseline, Folgetagsvergleich und Session-Warm-up

Stand 11.11.2026, Server Europe/Berlin. Fortführung ab Commit `7e40501`.

## 1. Baseline tatsächlich angewendet

- Vollständiger Wochenlauf `run-cardmarket-identity-weekly.py --apply` wurde
  **am 11.11.2026** während der regulären Sperrpause über
  `run-cardmarket-identity-guarded-once.py` erfolgreich ausgeführt.
- Offizieller `price_guide_6.json`: `2026-11-11T02:45:38+01:00`.
- Gespeicherte vollständige Guide-Baseline:
  `%LOCALAPPDATA%/Cardyssey/CardmarketCollector/cardmarket-guide-delta-state.json`
  mit **64.358** gültigen Produktpreis-Paaren (avg30 und trend).
- Erste Delta-Skip-Werte: DE 0, EN 0, erwartbar mangels früherer Guide-Baseline.
- Queue-Neugenerierung hat 1.717 DE und 274 EN ursprünglich manuell
  angeforderte Prüffälle erhalten. Die neu eingebaute
  `preserve_manual_scan_requests`-Prüfung lehnt den Verlust solcher Karten ab.
- Beide Fortschrittsdateien blieben bytegleich, Browser nicht neu gestartet
  oder gestoppt, **keine** neuen Cardmarket-Preise publiziert.
- Vorherige Queue-/Progress-Sicherungen:
  `/home/tv/cardshop/backups/cardmarket-guide-baseline-20261111/`.
- `tcg_price_cache.base_eur`, `updated_at` und `next_attempt_at`
  werden durch das Delta-Gate nicht künstlich angepasst. Der Guide ist eine
  Change-Detection-Quelle, kein frisch sprach-/druckverifizierter Preis.

### Nachtrag: Preisstaffel für Delta-Skips (11.11.2026)

Die Skip-Schwelle richtet sich nach dem letzten bestätigten DE-/EN-Preis:
unter 5 € gelten strikt unter 10 % Preisguide-Bewegung; von 5 € bis unter
15 € müssen **sowohl unter 3 % als auch unter 0,30 €** pro `avg30` und
`trend` eingehalten werden; ab 15 € wird immer im Browser geprüft.
12 € → 11,50 € bleibt daher scanpflichtig. Die Guide-Prüfung schreibt
weiterhin keine veröffentlichten Preise oder Preis-Zeitstempel um.

## 2. Einmaliger Folgetagsvergleich – 12.11.2026

- Tiny-`crontab`: am **12.11.2026** 08:05, 09:05, 10:05, 11:05 Uhr,
  über ein festes Tagesdatum begrenzt. Keine täglichen Pollings, höchstens
  vier Versuche falls Guide noch unverändert oder Scanner belegt ist.
- `scripts/cardmarket/core/cardmarket-next-day-delta-20261112.py` lädt den S3-Guide frisch
  vom offiziellen Server, verlangt einen tatsächlich **neueren `createdAt`**,
  errechnet im ersten Schritt **rein lesend** sichere Skips.
- Bei gerade laufendem Scanner **nur Vorschau**, niemals Queue-Mutation.
  Wenn keine Windows-Scannerprozesse laufen und die letzte Progress-Datei
  ebenfalls keinen aktiven Lauf zeigt, darf
  `run-cardmarket-identity-guarded-once.py` den Wochenlauf
  mit Backup, Sperre und Rollback durchführen.
- Ergebnis:
  `CardmarketCollector/cardmarket-next-day-delta-report-20261112.json`.
  Ein erfolgreicher tatsächlicher Apply wird zusätzlich idempotent in
  `cardmarket-next-day-delta-applied-20261112.json` dokumentiert.
  Die Admin-Ansicht trennt **Vorschau-Skips** von tatsächlich
  **angewandten Browser-Skips**. Beides ist keine neue Preisverifizierung.
- Eine ChatGPT-Aufgabe prüft den Status am 12. November gegen 10 Uhr und
  berichtet die Werte, ohne einen doppelten Lauf zu starten.

## 3. Sitzungs-Warm-up

- `Cardmarket-Session-Warmup.ps1` navigiert nach Ablauf aller Schutzpausen
  **einmal** im bereits offenen Cardmarket-Edge-Tab auf
  `https://www.cardmarket.com/`, wartet **6 Sekunden**, meldet
  `READY_FOR_HEALTH_CHECK` nur bei bestätigter Navigation.
- Bei sichtbarer Challenge, fehlendem Tab, Verbindungs-/Navigationsfehlern
  gibt es keinen Scanstart. Passwörter, Cookies und Token werden nicht
  gelesen oder manipuliert; keine Captcha-/Challenge-Umgehung.
- Anschließend entscheidet unverändert
  `Cardmarket-Session-Status.ps1` nur bei
  `AVAILABLE` **und** `AUTHENTICATED`, dass der Runner starten darf.
- `MinRequestGapSeconds=10`, `BatchLimit=16`, normale Pausen und die
  4-Stunden-Sperrpause bei `BLOCKED` bleiben unverändert.
- Der Warm-up wurde nur syntaktisch und hinsichtlich der Reihenfolge getestet;
  sein tatsächlicher Einfluss auf Cloudflare-Challenges ist nicht bewiesen.

## Tests

`python3 -m unittest discover -s scripts/cardmarket/tests -q`:
**176 Tests bestanden, 1 optionaler Test übersprungen**.
Zusätzlich Python-Kompilierung, PowerShell-Parser und TypeScript geprüft.
