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

## Update: 2026-11-06 – Vollständiger Angebotsmedian und Nachladeprüfung

- Im Browser vorhandener Button `#loadMoreButton` sendet ein Formular mit `Product_LoadMoreArticles`, `page`, `filterSettings` und Produkt-ID. Keine öffentliche, unbegrenzte Offer-API festgestellt.
- Cardmarket weist auf der Produktseite darauf hin, dass nur die ersten **300 Artikel** gezeigt werden; 300 Zeilen sind daher **kein** Nachweis für Vollständigkeit.
- Der neue DE-/EN-Prüfcollector klickt den vorhandenen Button, wartet auf mehr Angebotszeilen und prüft die Filter nach jedem Nachladen.
- Jede berücksichtigte Zeile benötigt eindeutige `articleRow...`-ID, korrektes Sprachlabel, NM/MT, geforderte Reverse-/Edition-Kennzeichnung und einen lesbaren Preis.
- Bei Blockierung, fehlendem Zuwachs, 300er-Grenze oder anderen Ausnahmen: `all_pages_complete=false`, `median_all_offers_eur=null`, nur Stichprobe zur Prüfung.
- Der zuvor implementierte offline Medianrechner `scripts/cardmarket-median-all-offers.py` verwendet jedes Angebot exakt einmal, nicht die angebotene Stückzahl.
- **Live-Limit:** Aktuelle Browser-Sitzung wurde als nicht angemeldet erkannt; ein Klick auf „Zeige mehr Angebote“ führte dort zu keinem Zeilenzuwachs. Nach erfolgreichem Cardmarket-Login ist eine erneute echte Nachladeprobe erforderlich.
- Diese Änderung schreibt weiterhin **keine** nicht abgesicherten Variantenwerte in den öffentlichen Preis-Cache.

## Live-Nachprüfung 2026-11-06 13:43 MEZ

- Remote Tiny online; `65575bc` als Ausgangsstand bestätigt.
- Der isolierte Edge-CDP-Port 9223 hat eine Cardmarket-Lucario-Produktseite geöffnet.
- Kein explizites Logout-/Account-Merkmal im DOM erkennbar; Collector meldet `LOGIN_REQUIRED`. Ein Login in einem anderen Browserfenster wird **nicht** in das isolierte Edge-Profil übertragen. Bestehendes Profil bleibt erhalten; keine Cookie-Extraktion oder Cloudflare-Umgehung.
- Begrenzte anonyme Diagnose mit genau einem Lucario-Fall und vorab bestätigter Produkt-URL: 50 deutsche NM-Angebotszeilen akzeptiert, niedrigster Listenpreis 0,04 EUR, Stichprobenmedian 0,15 EUR. Ein Klick auf `#loadMoreButton` führte nicht zu zusätzlichen Zeilen: `LOAD_MORE_NO_NEW_OFFERS`, `all_pages_complete=false`, `median_all_offers_eur=null`. Diese Daten sind **keine vollständigen Variantenpreise** und werden nicht veröffentlicht.
- Direkte geprüfte Queue-URL kann jetzt die fehleranfällige Textsuche überspringen; die tatsächliche `idProduct` bleibt vor jeder Auswertung gegen die verifizierten IDs zu validieren.
- Testbasis: 16 Tests der Variantenfilter und des vollständigen Medians bestanden; DE/EN-Medianberechnung nutzt jede eindeutige Angebots-ID einmal und veröffentlicht bei unvollständiger Pagination nichts.
- Für echten Live-Nachladetest ist die Anmeldung im **separaten CardmarketEdgeProfile-Browserfenster** erforderlich. Kein automatische Wiederanmeldung und kein Challenge-Bypass vorgesehen.

## Login erfolgreich – Nachladetest 2026-11-06, 13:47 MEZ

- Im isolierten Edge-CDP-Browser ist jetzt die Anmeldung nachgewiesen (`AUSLOGGEN` sichtbar).
- Lucario MEP 095, Deutsch, minCondition=2: Von 50 auf 251 DOM-Angebotszeilen nachgeladen, alle 251 Zeilen mit deutschem Sprachlabel und NM/MT verifiziert.
- Stichprobenmedian dieser 251 Angebote: 0,49 EUR; niedrigstes Angebot 0,04 EUR; Median der fünf günstigsten: 0,05 EUR.
- Nach sechs Seitenversuchen kam keine weitere Zeile hinzu. Der DOM-Check zeigte `#loadMoreButton` als `disabled`, `d-none`, `display:none` bei `articlePage=5` und einen Cardmarket-Hinweis, dass nur die ersten 300 Artikel angezeigt werden. Ohne Beweis für eine erschöpfte ungecappte Angebotsmenge bleibt `all_pages_complete=false`, `median_all_offers_eur=null`.
- Collector erkennt nun deaktivierte/versteckte Nachladebuttons ausdrücklich als `LOAD_MORE_DISABLED_OR_LIMIT_REACHED`, statt erfolglose Klicks als erfolgreiche Seitenpagination zu interpretieren.
- Sicherheitsstandard: keine Cloudflare-Umgehung, keine Cookie-Exporte, kein Import unvollständiger Printpreise in den produktiven Preis-Cache.

## Automatischer öffentlicher Fallback und regulärer DE/EN-Runner (2026-11-06)

- Browser-CDP erkennt Login sprachunabhängig am Link `User_Logout`, nicht am deutschen Text. Das funktioniert für die deutsche und englische Cardmarket-Oberfläche.
- Ohne Login bleibt der Collector aktiv (`access_mode=PUBLIC_LIMITED`), wendet verfügbare öffentliche Sprach-/Zustandsfilter an, erfasst IDs und Preisstichproben und unterdrückt den vollen Median (`all_pages_complete=false`, `median_all_offers_eur=null`, `pagination_failure=PUBLIC_SESSION_LIMITED_SAMPLE`). Keine automatische Anmeldung und keine Cloudflare-Umgehung.
- Echtes unangemeldetes Browserprofil auf Port 9222 getestet: Lucario MEP095 DE, 50 bestätigte Angebotszeilen, `PUBLIC_LIMITED`, kein veröffentlichter Gesamtmedian.
- Angemeldeter Edge-Browser auf Port 9223 getestet: Lucario MEP095 EN, 26 Sprach-/Zustands-geprüfte Angebotszeilen, ein vollständiger *Angebots*median von 1,86 EUR, weiterhin `PRINT_UNVERIFIED`, nicht im produktiven Kartenpreis.
- Tangela sm10-16 DE: Reverse mit 8 geprüften Angeboten (Median 0,32 EUR), Normal mit 44 geprüften Angeboten (Median 0,15 EUR). Keine Vermischung beider Varianten; bis zur Print-Freigabe keine Cache-Veröffentlichung.
- Der bisherige Windows-Launcher wurde vor Austausch gesichert. Neuer Launcher startet `Cardmarket-Queue-Runner.ps1`, welcher die DE-/EN-Warteschlangen sequenziell in Chargen von 40 fälligen Varianten mit 8 Sekunden Grundabstand abarbeitet. `progress-de.json` und `progress-en.json` halten den unabhängigen Fortschritt. Bei Provider-Blockade/Verbindungsabbruch wird kein neuer Sprachlauf gestartet.
- Nur geprüfte Seiten werden als komplett markiert; verlorene Sitzungen werden während des Durchlaufs erkannt und als öffentliche Stichprobe degradiert.
- Die bestehenden 30.000+ Varianten werden so über mehrere Läufe gescannt; dieses Rolling-Verfahren ist **keine** Zusage, alle Varianten innerhalb von 7 Tagen zu aktualisieren. Der Preisguide bleibt die flächendeckende Basis.

## Laufzeitoptimierung (2026-11-06, search discovery cache)

- Gezielte Vorher-Nachher-Messung auf demselben isolierten Edge-Profil mit Tangela sm10-16 Normal + Reverse: Basis 14,46 s; optimierte Variante 14,70 s. Beide ergaben unverändert Reverse 0,32 EUR (8 Angebote) und Normal 0,15 EUR (44 Angebote). **Keine Beschleunigung behaupten** für diesen Fall: Die zweite Variante konnte bereits eine gesicherte Produkt-URL wiederverwenden, dadurch 0 Search-Cache-Hits.
- In der DE-Warteschlange sind 16.662 browser-relevante Varianten, aber nur 11.388 unterschiedliche Suchbegriffe (Name + Nummer). 5.274 wiederholte Suchbegriffe sind ein theoretisches Maximum; gesicherte Produkt-URLs und nicht zusammenliegende Fälle verringern realen Effekt.
- Collector cached ausschließlich unveränderte **Suchseiten-Linklisten** pro exakter Such-URL, begrenzt auf 250 Einträge pro Prozess. Jeder Kandidat wird weiterhin gegen die erlaubten Cardmarket-IDs geprüft; gefilterte Angebote, Normal/Reverse/Edition, Median, Login und Preisvalidierung werden **nicht** gecached.
- Einzelne Search-Navigations-Timeouts werden jetzt als `DEFERRED_PROVIDER_TIMEOUT` gespeichert, anstatt bei erster langsamer Karte alle Folgekarten abzubrechen. Drei aufeinanderfolgende Suchtimeouts bleiben ein harter Sicherheits-Stopp (`PROVIDER_TIMEOUT`); explizite BLOCKED-Erkennung ist unverändert.
- Neue Diagnostik pro Karte: `search_cache_hit`, `elapsed_ms`; pro QC: `search_cache_hits`, `search_cache_misses`. Die Standardabstände von acht Sekunden bleiben zum Schutz vor weiteren Provider-Timeouts erhalten.
- Ein experimenteller Produktseiten-DOM-Reuse wurde **nicht** übernommen, weil der zweite Tangela-Lauf veraltete Filterangebote zurückgab. Damit bleibt das Verhalten korrekt.
- 22 Unit-Tests für Collector/Median und Windows PowerShell Parser erfolgreich, Produktionskopie ersetzt; sichere Preisübernahme bleibt weiterhin getrennt von Browserstichproben.
