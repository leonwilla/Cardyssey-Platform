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

**Stand 23.11.2026**
- Repos aufgeräumt (PR #24 hier, PR #15 in der App).
- **Größte Baustelle:** Shop fertigstellen. Eigener Shop zeigt Angebote, hat aber noch keinen Warenkorb, keine Zahlung, keine Bestellungen; Zahlungsanbieter noch nicht gewählt. Live-Shop ist weiterhin WordPress/WooCommerce.
- Preis-Pipeline sehr verzweigt (viele Quellen, über 20 Recovery-Runden). Nicht weiter ausbauen, bevor geklärt ist, welche Quellen produktiv gebraucht werden. Cardmarket-Scraping auf Nutzungsbedingungen prüfen.
- Offen: Server-Bestandsaufnahme (Container, Dienste, Timer, Cronjobs, welche Skripte wirklich laufen); ~270 fest eingetragene `/home/tv/...`-Pfade; `generated/` und `web/lib/generated/` sind trotz `.gitignore` eingecheckt; `selenium/standalone-chromium:latest` pinnen.
