# Cardyssey – Cardmarket DE/EN-Sprachfiltertest (2026-11-06)

## Ergebnis

Die öffentlichen Cardmarket-Produktseiten wurden im bestehenden Browserprofil
anhand von drei Produktseiten je zweimal mit genau einem Sprachfilter geöffnet:

- Deutsch: `language=3&minCondition=2`
- Englisch: `language=1&minCondition=2`
- `minCondition=2` bedeutet Mint **oder** Near Mint, nicht ausschließlich Near Mint.
- Filter müssen wirklich angewendet und auf den geladenen Angebotszeilen geprüft werden.
- Der Cardmarket-Produkt-Identifier bleibt bei den beiden Sprachen identisch.

| Cardmarket-Produkt | ID | DE Angebote sichtbar | EN sichtbar | DE günstigstes Angebot | EN günstigstes Angebot | DE Median der 5 günstigsten | EN Median der 5 günstigsten |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mewtu Basis-Set | 273705 | 49 | 44 | 59,00 € | 50,00 € | 62,99 € | 95,00 € |
| Vulnona Basis-Set | 273707 | 50 | mindestens 50 | 17,77 € | 29,64 € | 25,00 € | 30,88 € |
| Lucario MEP095 | 895610 | mindestens 50 | 26 | 0,04 € | 0,87 € | 0,05 € | 0,98 € |

Achtung: Die Browseransicht zeigt maximal einen Ausschnitt der Angebote;
die Zahlen sind **aktive Angebotspreise**, keine tatsächlichen 30-Tage-Verkäufe.
Der Median bezieht sich auf die fünf günstigsten der sieben einzeln
sprach- und zustandsbestätigten Angebotszeilen aus dem Test.
Die genaue Normal-/Holo-/Reverse-/Edition-Identität wurde für diese
Stichprobe NICHT bestätigt; keine Preisübernahme in den Sammlungs-Cache.

## Behobene Fehler im Collector

1. Vorher wurden beim erneuten Filtern bereits angehakte andere Sprachen
   nicht abgewählt. Jetzt wird nur die Zielsprache angehakt.
2. Vorher konnte ein gesetztes Kontrollkästchen vor Abschluss des Filterrequests
   als erfolgreich gewertet werden. Jetzt müssen auch die URL-Parameter
   (`language`, `minCondition`) und die einzelnen Angebotszeilen stimmen.
3. Bei deutschen Cardmarket-Seiten lautet das Sprachlabel der englischen
   Angebotszeilen `Englisch`, nicht `English`. Beide Begriffe werden erkannt.
4. Währungsformate wie `1.234,56 €` und `1,234.56 €` werden korrekt geparst.
5. Neue Ergebnisfelder: `lowest_ask_eur`, `entry_five_median_eur` –
   die bisherigen Browser-Stichproben bleiben bis zur Print-Verifizierung
   ausdrücklich Prüfkandidaten.

## Speicherung und Tests

- Die sechs geprüften Kombinationen liegen in
  `cardmarket_language_offer_samples` (Migration V59); die Spalten
  `print_scope=UNVERIFIED_PRINT_VARIANTS` und
  `price_basis=ACTIVE_ASKING_NOT_SOLD` verhindern falsche Interpretation.
- Die Preise wurden **nicht** in `tcg_price_cache` veröffentlicht.
- Auswertung: `python3 scripts/verify-cardmarket-language-browser-smoke.py`
- Test: `python3 scripts/test_verify_cardmarket_language_browser_smoke.py`
- Staging: `python3 scripts/import-cardmarket-language-probes.py --apply`
- Collector-Kopien: `scripts/cardmarket-language-browser-collector.ps1` (DE/EN)
  und `scripts/cardmarket-edge-browser-collector.ps1` (aktiver DE-Runner).
- Die entsprechenden aktiven Dateien unter
  `C:\Users\TV\AppData\Local\Cardyssey\CardmarketCollector`
  wurden aktualisiert und davor gesichert.

## Grenzen

Der Cardmarket-Preisguide liefert keine eigenen Preise pro Sprache/Zustand.
Die neue Browser-Lösung kann solche Angebotspreise getrennt erfassen,
aber ein zuverlässiger flächendeckender Wochenbetrieb und die Prüfung
von Edition, Reverse, Holo, Stempeln sowie unvollständigen Seiten
sind **noch nicht** als beendet oder vollautomatisch freigeschaltet.
