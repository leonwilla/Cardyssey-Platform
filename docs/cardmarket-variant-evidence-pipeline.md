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
