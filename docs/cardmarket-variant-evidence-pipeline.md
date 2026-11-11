# Cardmarket: Varianten-Evidenz und Preisprüfung

Stand: 2026-11-11. **Keine** automatische Bestätigung nur nach V1/V2,
Preisabstand, pHash oder fehlendem Verkäuferkommentar.

## Quellen und Beweise

1. Offizieller Product-List-Feed: idProduct, idExpansion und idMetacard.
   idMetacard ist die *Kartenfamilie*, nicht der physische Druck.
2. Cardmarket `/Cards/.../Versions`: beobachtete URLs, Haupt- und
   Additionals-Erweiterungen, geöffnete Produktseite und kartennummerbasierte
   Kandidaten. Ein V2-Suffix ist keine allgemeine Meisterball-Regel.
3. Korrekte Produktseite: unabhängiger Live-Produkt-ID-Abgleich, Setpfad,
   Kartennummer und ggf. eine strukturierte, eindeutige Print-Bezeichnung.
4. Bilder: optionaler pHash ist **nur ein Ähnlichkeitssignal**. Dieselbe
   Illustration mit anderem Folienmuster kann fast identische Hashes haben.
   Ein Bildbeweis muss den relevanten Folien-/Stempelbereich eindeutig
   identifizieren und darf nicht automatisch aus der pHash-Distanz entstehen.
5. Verkäuferkommentare: explizites "Master Ball" ist ein Hinweis,
   "nur Pokéball" widerspricht. Leere Kommentare sind ungeklärt.
   Insbesondere ist bei japanischen Reverse-Angeboten fehlender
   Meisterball-Text **kein** sicherer Pokéball-Beleg.

## Datenhaltung

* `cardmarket_variant_mappings`: Produktkandidaten und **manuell
  bestätigte** Drucke strikt getrennt. Unique-Constraint verhindert zwei
  bestätigte IDs für dieselbe Cardyssey-Variante.
* `cardmarket_variant_offer_diagnostics`: nur Diagnosewerte aus aktiven
  Angebotspreisen, niemals Verkaufsdaten oder direkte Sammlungswerte.
* `cardmarket-verified-print-mapping-cache.json`: nur HUMAN_CONFIRMED,
  erneuert bei Review/Undo und wöchentlichem Identitätslauf.
* `cardmarket-metacard-family-index.json`: lokale Kandidatenfamilien
  für DE/EN aus dem offiziellen Produktkatalog. Prüft keine Sonderfolien.

## Preisdiagnose

1. Sprache und NM/Mint (keine EX/Played/Poor) einzeln pro Angebot prüfen.
2. idProduct, Reverse, bearbeitete/gradierte Karten und Bundles kontrollieren;
   für besondere Muster eindeutige Verkäuferkommentare verlangen.
3. Vollständige Pagination, eindeutige Angebots-IDs und alle passenden
   Angebote prüfen. Partieller Auszug ist niemals Marktmedian.
4. Gesamten Median berechnen; optionaler IQR nur als Diagnose bei mindestens
   acht akzeptierten Angeboten. Die fünf günstigsten Angebote oder eine
   pauschale Kürzung von 20% sind kein Ersatz für den Marktmedian.
5. Offizieller Cardmarket-Trend ist produktweit, nicht automatisch
   deutsch/englisch und nicht druck-/zustandsspezifisch; nur Plausibilitätswarnung.
6. Preise bleiben ungeprüft, bis die physische Druckvariante unabhängig
   bestätigt ist.

## Betrieb und Grenzen

* `scripts/cardmarket_variant_resolver.py`: konservative Klassifikation,
  Kommentare, Preisdiagnose; keine DB-Preisänderungen.
* `scripts/cardmarket-build-metacard-family-index.py`: ganzer DE/EN-Katalog
  als lokaler Kandidatenindex ohne neue Browserabfragen.
* `scripts/cardmarket-sync-print-mapping-cache.py --apply`:
  bestätigte Identitäten und offene Versionskandidaten in DB; nur bestätigte
  Identitäten werden in den Scanner-Cache exportiert.
* `scripts/cardmarket-language-browser-collector.ps1`: liest eindeutige
  Produktzuordnungen und kommentiert Sonderdruck-Anzeigen im Monitoring.
* Bei LOGIN_REQUIRED oder Cloudflare-Sperre wird regulär pausiert; kein
  Proxy-/Challenge-Bypass. Neue Angebotsseiten können erst nach normaler
  Freigabe und erfolgreichem Login geprüft werden.

## Persistentes Login & schonende Scanpakete (2026-11-11)

* Der Windows-Scanner verwendet weiterhin **dasselbe dedizierte
  Cardmarket-Edge-Profil** unter `%LOCALAPPDATA%\Cardyssey\CardmarketEdgeProfile`.
  Kein Passwort-Bot und kein Cookie-/LocalStorage-Export; auch ein gespeicherter
  Login garantiert **keinen** Cloudflare-Zugriff.
* `Cardmarket-Session-Status.ps1` unterscheidet eine echte sichtbare
  Login-Maske von einer Provider-Sperrseite, einschließlich der Textmeldung
  `You have been blocked`. Bei unklaren Zuständen wird kein Gast-Scan
  und kein automatischer Login ausgeführt.
* 10 Sekunden **Mindestabstand zwischen den wichtigen Provider-Anfragen**
  (Seitennavigation, Direkt-ID-Lookup, Formularfilter, AJAX-Nachladebutton),
  zusätzlich zu den bestehenden Kartenpausen. Das ist kein versprochener
  stündlicher Durchsatz und vermeidet nicht zwangsläufig Anbietergrenzen.
* Scanpakete: 16 Karten pro Sprachbatch, DE/EN abwechselnd, begrenzte
  Laufsitzung von rund 40 Minuten (Grenze wird zwischen Batches geprüft).
* Reguläre Wiederaufnahme frühestens 45 Minuten nach einem abgeschlossenen
  unvollständigen Batch; nach `BLOCKED` frühestens nach vier Stunden,
  nach Provider-Timeout 90 Minuten. Der Watchdog kontrolliert beide Sprachen
  und prüft vor Wiederaufnahme die tatsächliche Browsersitzung.
* `cardmarket-prioritize-recovery-queue.py` sortiert die Warteschlangen
  ohne Datenverlust: offene Variantenfamilien (Felori, Wattzapf etc.),
  bereits bestätigte Sonderdrucke, andere Fehlerfälle, dann gewöhnliche
  und Bulk-Karten. Der bestehende Prüfzeitpunkt und die Preisquellen bleiben
  unverändert. Neue offene Metakartenfälle werden **einmalig** fällig gestellt;
  kein endloses Zurücksetzen der Scan-Zeitstempel.
* Der wöchentliche Identitätslauf wendet die Priorisierung nach einem
  erneuten CSV-Export wieder an.

## Scanner-Optimierung nach externem Code-Review (11.11.2026)

**Grundsatz:** Keinen Sicherheitsmechanismus umgehen, keine Druckvariante
allein aus Kurztext/Preis ableiten, keine Karten/Preise bei Queue-Optimierung
löschen. Bei 403/429/503 und Cloudflare-Challenges bleibt der Lauf pausiert.

### Bulk ohne Browser, aber weiterhin im Katalog

Im aktuellen Bestand sind **15.060 DE und 16.168 EN** normale, bereits
bepreiste Bulk-Varianten als `FEED_ONLY` für die Browserprüfung geeignet.
Die neun noch unbepreisten Bulk-Varianten bleiben im Browser-Backlog.
Ein manueller Scanwunsch übersteuert diesen Skip. Die CSV selbst bleibt
vollständig und enthält alle 65.647 Varianten; keine Daten gehen verloren.
Der Monitor zeigt ab jetzt die wirklich browserberechtigten Positionen
(DE 16.381 / EN 18.038 auf Basis der Inventur vom 11.11.2026),
nicht mehr die vollständige Katalogmenge als vermeintlichen Browser-Backlog.
Eine bereits bepreiste Bulk-Karte hat dadurch noch **keine** separat
verifizierte Cardmarket-Produkt-ID; dieser Unterschied bleibt sichtbar.

### Einmal validierte Produktseiten sprachübergreifend nutzen

`scripts/cardmarket-build-cross-language-page-cache.py` liest ausschließlich
lokale DE/EN-Queue- und Beobachtungsdaten. Eine wiederverwendbare URL
benötigt **beidseitig denselben Cardyssey-Karten-/Variantenbezeichner**,
identische offizielle `catalog_singleton_id` und `catalog_expansion_id` sowie
einen unabhängigen Live-Beleg für ID und Kartennummer an der Quellseite.
Sonderdrucke und unbestätigte Metakarten-Kandidaten werden hier nicht
stillschweigend übernommen. Die Zielseite muss Produkt-ID und Kartennummer
noch einmal selbst verifizieren und ihre Sprach-/Reverse-Filter neu anwenden.
Erster Quervergleich: 165 sichere *Seitenkandidaten*; **0** dadurch neu
bestätigte Sonderdrucke oder Preise. Der Runner versucht den Cache nach
jedem erfolgreichen Sprachbatch lokal über WSL zu erneuern; wenn WSL nicht
antwortet, bleibt der letzte Index erhalten und der Scanner nutzt seine
vorhandenen normalen Suchrouten.

### Leichte Suchabfrage mit Fallback

`scripts/cardmarket-lightweight-search.ps1` versucht zunächst eine
same-origin HTML-Suchabfrage **im bereits angemeldeten Browserkontext**.
Sie verwendet keine exportierten Cookies, keine Browserfingerprint-Fälschung,
keine Captcha-/Cloudflare-Umgehung. Ergebnisse aus HTML werden nur als
Suchkandidaten gewertet. Rendert Cardmarket die Treffer erst nachträglich
im DOM oder fehlen belegbare Suchtreffer, fällt der Scanner auf die bereits
bewährte vollständige Navigation zurück. 403/429/503 sind Abbruchzustände.
Der Server muss diese Abrufart natürlich zulassen; ein garantierter
Zeit-/Bandbreitengewinn ist damit nicht belegt.

### Kommentarkürzel synchron und beweissicher

`config/cardmarket-comment-rules.json` ist jetzt die einzige Regex-Quelle
für Python und PowerShell. `MB`/`PB` alleine bedeuten **SHORTHAND_HINT**,
keine automatisch verifizierte physische Druckvariante. Eindeutig
anders beschriftete oder negierte Kommentare werden ausgeschlossen.
Der aktive Angebotspreis-Diagnostiker kann einen Shorthand-Hinweis nur bei
zuvor unabhängig bestätigter Druckvariante berücksichtigen.

### Archiv

Sechs nicht mehr referenzierte Prototypen wurden in `scripts/archive/`
verschoben; aktive Skripte, Tests, Quellpreise und Scanwarteschlangen
bleiben unverändert.
