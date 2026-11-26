# Cardyssey Platform – Anweisungen für Claude

Antworte auf Deutsch, in einfachen Worten. Der Inhaber ist kein Vollzeit-Entwickler: erkläre kurz, was du tust und warum, und frag nach, bevor du etwas Riskantes machst.

## Projekt

Cardyssey = Pokémon-Sammelkarten-Plattform: Sammlung, Scanner, Preise, Marktplatz, Shop.

- **Dieses Repo** (`leonwilla/Cardyssey-Platform`): Webapp, Admin, Shop, Backend, Preis-Pipelines
- **`leonwilla/Pokemonkarten-APP`**: Android-App (Kotlin/Compose, Paket `de.cardfolio.app`, nicht umbenennen)
- **`leonwilla/Cardyssey-Downloads`**: APK-Verteilung (nur README; APKs kommen über den eigenen Runner auf den Server)

| Teil | Ort | Technik |
|---|---|---|
| Web, Admin, Shop | `web/` | Next.js 16, React 19, Port 3000, Dienst `cardyssey-web.service` |
| Backend-API | `platform/api/` | Kotlin/Ktor, PostgreSQL, Flyway (`src/main/resources/db/migration`, fortlaufend `V<n>__name.sql`) |
| Container | `platform/compose.yml` | Postgres (127.0.0.1:5433), API (127.0.0.1:8081), Browser-Worker (7900) |
| API-Vertrag | `contracts/cardyssey.openapi.json` | → `make generate` erzeugt Clients für Web und App |
| Skripte | `scripts/` | Preise, Katalog, Wartung, Deploy; viele davon laufen per systemd/Cron/Workflow |
| Altes WordPress | `compose.yml` (Root), `theme/` | Live-Shop bis zum Cutover, **nicht anfassen** ohne Rückfrage |

Domains: `cardyssey.de` (Web/API), `shop.cardyssey.de` (neuer Shop).

## Server („Tiny“)

- Lenovo Tiny, Windows + WSL Ubuntu, läuft 24/7, Benutzer `tv`
- Live-Repo: `/home/tv/cardshop`; Backups: `/home/tv/cardyssey-backups`; eBay-Collector: `/home/tv/cardyssey-ebay-collector`
- **Auto-Deploy:** `cardyssey-deploy.timer` → `scripts/cardyssey-deploy-safe.sh` macht `git pull --ff-only origin main`, baut in `releases/web-*` und schaltet `cardyssey-web.service` um

## Regeln

1. **Nie direkt auf `main` committen oder pushen.** Alles auf `main` geht automatisch live. Immer: Branch → Pull Request → CI grün → Merge.
2. **Im Live-Ordner `/home/tv/cardshop` keine Dateien bearbeiten.** Sonst scheitert `git pull --ff-only` und das Deployment bleibt stehen. Arbeiten in einem eigenen Klon oder `git worktree`.
3. **Keine Zugangsdaten ins Repo.** Geheimnisse gehören in `.env` auf dem Server (Vorlage `web/.env.example`).
4. **Vor dem Löschen von Skripten** prüfen, ob sie von systemd, Cron, `.github/workflows/` oder anderen Skripten genutzt werden.
5. **Datenbank:** Schemaänderungen nur als neue Flyway-Migration, nie bestehende Migrationen ändern. Vor riskanten Änderungen Backup prüfen.
6. **Zahlungen:** Nie selbst Kartendaten verarbeiten; externer Zahlungsanbieter mit gehostetem Checkout (siehe `docs/SHOP_WITHOUT_WORDPRESS_ARCHITECTURE.md`).
7. Bei Unklarheit lieber nachfragen als raten.
8. **Nur Claude.** ChatGPT/Codex wird nicht mehr verwendet: keine Codex-Automatisierungen, keine ChatGPT-Logins, keine Skripte dafür neu anlegen.
9. **Mergen:** Claude darf eigene PRs selbst mergen, wenn die CI grün ist und sie nur Doku, Tests oder Aufräumen betreffen. Alles, was live etwas am Verhalten ändert (Web, API, Datenbank, Cron, systemd), erst nach kurzem OK des Inhabers mergen.

## Prüfen vor einem PR

```bash
cd web && npm ci && npm run build                     # Web
cd platform/api && gradle test                         # Backend (CI nutzt gradle:8.13-jdk21 in Docker)
make verify                                            # API-Vertrag passt zum Code
```

## Wichtige Doku

- `docs/SHOP_WITHOUT_WORDPRESS_ARCHITECTURE.md`: Zielbild Shop (Warenkorb, Zahlung, Bestellungen)
- `docs/SHOP_STANDALONE_HOST_CUTOVER.md`: Umstieg von WordPress
- `docs/TINY_CONTAINERS.md`, `docs/NATIVE_SHOP_TINY_RELEASE.md`: Server und Deployment
- `docs/archive/`: abgeschlossene Analysen und Protokolle (nur bei Bedarf lesen)

## Aktueller Stand

> Diesen Abschnitt am Ende jeder Arbeitssitzung kurz aktualisieren (per PR).

**Stand 26.11.2026**
- Repos aufgeräumt (PR #24 hier, PR #15 in der App). Server-Bestandsaufnahme gemacht: Server stabil, Deploy läuft.
- **TCG-Preise (PR #28, 24.11.):** Cardmarket-Scan holt Produktadressen jetzt aus Cardmarkets Erweiterungslisten statt über die Suche (die löste fast alle Cloudflare-Blocks aus). Browser-Scan ab 2 € (darunter offizieller Richtwert), Neu-Scan nach Wert. Varianten: automatisch, wenn per Reverse/1.-Auflage-Filter eindeutig; sonst gruppierte Prüfliste `reports/cardmarket-variant-review-groups.csv`, eine Zeile in `config/cardmarket-variant-version-rules.json` löst eine ganze Gruppe (Base Set V1=Unlimited, V2=Schattenlos schon eingetragen). Doku: `docs/CARDMARKET_IDENTITY_AND_PRICE_PIPELINE.md`.
- Für Live-Tests darf der laufende Cardmarket-Scanner sofort gestoppt werden (Tests haben Vorrang).
- **Cloudflare (24.11.):** Freigabe läuft bei Cardmarket fest nach ~60 min ab (Cookie wird gespeichert, hilft aber nicht). Scanner wartet jetzt ruhig ab, startet erst nach echter neuer Freigabe, Telegram nach 5 min, Login bleibt über Edge-Neustarts. Kein Umgehen der Prüfung.
- **Monitoring (24.11.):** Block „Set-Listen-Scan“ im Admin (Tempo, Fortschritt, Prüfgruppen-CSV, Zeitpunkt für Komplett-Neuscan). Alte Fehlfälle mit neuer Adresse werden automatisch neu gescannt; unter 2 € und bei Cardmarket nicht trennbare Sonderdrucke raus aus der Prüfliste. `reports/cardmarket-expansion-index-apply.json` und `…-review-groups.csv` sind Laufzeitdateien (nicht mehr im Repo).
- **Preise (24.11. abends):** Alle DE/EN-Karten mit geprüfter Cardmarket-ID bekommen alle 2 h den offiziellen Cardmarket-Preis-Trend (`publish-cardmarket-guide-prices.py`, Quelle `CARDMARKET_GUIDE`, kein Multiplikator, Rücksicherung in `/home/tv/cardyssey-backups/cardmarket-guide-prices`). Browser-Scan nur noch ab 20 € für den exakten Preis nach Sprache. **DE/EN zeigen nur Cardmarket-Preise** (TCGdex & Co. entfernt, API-Worker für DE/EN gesperrt, Anzeige-Sync nur `CARDMARKET%`); Karten mit 1. Auflage scannt der Browser.
- **24./25.11.:** TCGdex als Preisquelle komplett entfernt (API-Preis-Worker aus, 17.063 Zeilen geleert, Sicherung `/home/tv/cardyssey-backups/tcgdex-prices-removed/`; Kartenkatalog/Bilder bleiben TCGdex). Browser-Neu-Scan nach Wert: ab 250 € täglich, ab 100 € wöchentlich, sonst 4 Wochen (gilt jetzt auch im Komplett-Neuscan). `scripts/cardmarket/` aufgeräumt (40 ungenutzte Skripte/Tests weg, `archive/` gelöscht). eBay: 60-Tage-Stufe ergänzt (30→60→90 T→6 M→1 J→jährlich); Sammler weiter von eBays Bot-Schutz blockiert, wird nicht umgangen; Antrag Marketplace Insights API vorbereitet (`/home/tv/ebay-marketplace-insights-ticket.txt`), Inhaber stellt ihn mit neuem Konto.
- **25.11. mittags:** Preisverlauf-Graph im Karten-Fenster (Markt TCG; 7 T/30 T/3 M/1 J/Alles). DB-Trigger (V61) schreibt jede Änderung eines DE/EN-Cardmarket-Preises in `tcg_price_history`, Startpunkt 25.11.; API `/api/v1/pricing/tcg-history/{id}`. Scanner: Filter in der Adresse wieder aktiv (vorher jeder Lauf ab Karte 1 aufs Formular, 2 statt 1 Aufruf je Karte), Telegram-Warnung kommt jetzt auch bei wiederkehrender Box. Abstand zwischen Aufrufen am 26.11. auf Wunsch des Inhabers von 11 auf 8 s gesenkt. Automatisches Klicken der Cloudflare-Box (Vorschlag Kollege) bewusst abgelehnt.
- **26.11. nachts:** Cardmarket-Preisliste wurde bis 25.11. immer einen Tag zu alt genutzt (Cache 20 h) – jetzt Prüfung per HEAD auf neuere Liste (PR #49). Prüffälle: Variante wird automatisch über die eindeutige Cardmarket-ID je Variante (TCGdex-Variantendaten) zugeordnet, mit Preis-Gegenprobe (Sonderdruck nicht deutlich billiger als normal) – Prüfliste DE 196→102, EN 226→131, dazu ~1.900 Varianten zusätzlich mit offiziellem Preis (PR #51). Rest sind echte Sonderfälle (z. B. Grundset-Pikachu mit 6 Versionen). Grundset-Karten mit 1. Auflage bekommen ihren Preis nur per Browser-Scan (Preisführer mischt 1. Auflage/Unlimited), das ist gewollt.
- **Preis-Plausibilität (26.11.):** Cardmarkets `trend` ist bei selten verkauften Karten teils kaputt (0,02 € bei 1.048 € 30-Tage-Schnitt) – liegt er > Faktor 2 neben avg7/avg30, gilt der Median der drei (PR #56, ~1.000 Preise korrigiert). Browser-Preise sind Median-*Angebots*preise; Werte > 10× (bei < 3 Angeboten > 4×) vom Preisführer werden nicht übernommen, der 2-h-Lauf ersetzt gespeicherte durch den offiziellen Preis (PR #57, `cardmarket_price_sanity.py`). 15 unplausible 1.-Auflage-Werte auf „kein Preis“ gesetzt, Sicherung `/home/tv/cardyssey-backups/browser-implausible/`. Alte Prüftabellen aufgeräumt (OK Inhaber 26.11.): 42.067 offene Einträge in `cardmarket_print_identity_review` und alle 1.542 in `price_review_cases` gelöscht, die 218 bestätigten Einträge bleiben; Tabellen selbst bleiben (Skripte/Admin lesen sie). Sicherung `/home/tv/cardyssey-backups/old-review-tables/`.
- **Set-Logos (26.11.):** 30 Sets ohne TCGdex-Logo (Delta-Herrschaft, 30 Jahre, Trainer-Galerien, Promos, McDonald's …) haben Ersatzlogos unter `web/public/set-logos/`, API setzt sie ein (`SetLogoFallbacks.kt`), Pfad ist ohne Anmeldung erreichbar. Nach API-Änderungen: `cd platform && docker compose up -d --build api` (Auto-Deploy baut nur das Web).
- **Design (26.11.):** Startseite, Anmeldung/Registrierung und Shop (shop.cardyssey.de) im Kartendeck-Look wie App/Webapp; alte Startseiten-Bausteine gelöscht. Webapp und App sagen Wunschliste/Vitrine/Marktplatz statt Wishlist/Showcase/Marketplace.
- **Bewusst zurückgestellt** (erst auf Ansage angehen): eBay-Preisabfrage (Healthcheck meldet seit 12.11. SERVICE_ERROR, Warnmails unterdrückt) und Shop (kein Warenkorb, keine Zahlung, keine Bestellungen; Live-Shop ist noch WordPress/WooCommerce).
- Erledigt am 23.11.: ChatGPT/Codex komplett entfernt (Cron-Eintrag, `scripts/codex-quality-repair.sh`, Codex-CLI, `~/.codex`). Tote Einzelaktions-Cronjobs (06.11./12.11.) entfernt, Sicherung der alten Crontab: `/home/tv/crontab-backup-20261123.txt`. Docker-Build-Cache geleert. `releases/` und `backups/` in `.gitignore`.
- Palworld: Container und Image entfernt. Spielstand gesichert und geprüft in `/home/tv/palworld-spielstand-20261123.tar.gz`; Originaldaten liegen weiter in `/home/tv/palworld-server/palworld-data`. `vinted-ingest` gehört zum separaten Vinted-Projekt, nicht ohne Rückfrage anfassen.
- Ungeklärt: `web/components/notify-form.tsx` und `games.tsx` (Herkunft unbekannt) sind im Draft-PR `wip/notify-form-games-sichern` gesichert, nicht mergen ohne Klärung.
- Ungenutzte Skripte (~90, siehe Bestandsaufnahme) noch **nicht** löschen, erst auf Ansage.
- Später: ~270 fest eingetragene `/home/tv/...`-Pfade; `generated/` und `web/lib/generated/` trotz `.gitignore` eingecheckt; `selenium/standalone-chromium:latest` pinnen; Next.js-Warnung zu Dateizugriff (bläht `releases/` auf); Cardmarket-Scraping auf Nutzungsbedingungen prüfen.
