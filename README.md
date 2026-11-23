# Cardyssey Platform

Webapp, Webshop und Backend für Cardyssey (Pokémon-Sammelkarten: Sammlung, Preise, Marktplatz, Shop).
Die Android-App liegt im Repo `Pokemonkarten-APP`, die APK-Downloads in `Cardyssey-Downloads`.

## Aufbau

| Ordner | Inhalt |
|---|---|
| `web/` | Next.js-Frontend (Webapp, Admin, Shop unter `shop.cardyssey.de`) inkl. API-Routen |
| `platform/api/` | Backend-API (Kotlin/Ktor, PostgreSQL, Flyway-Migrationen) |
| `platform/compose.yml` | Docker-Setup für Datenbank, API und Browser-Worker |
| `contracts/` | OpenAPI-Vertrag zwischen Backend, Web und App |
| `generated/` | Aus dem Vertrag generierter Android-Client (`make generate`) |
| `scripts/` | Preis-, Katalog-, Wartungs- und Deploy-Skripte (`scripts/cardmarket/`, `scripts/ebay-collector/`) |
| `config/` | Konfiguration für die Cardmarket-Pipeline |
| `ops/` | Dienste für den Server (systemd, Windows-Autostart) |
| `theme/`, `compose.yml` (Root) | Altes WordPress-Setup, läuft bis zum Shop-Cutover weiter (siehe `docs/SHOP_STANDALONE_HOST_CUTOVER.md`) |
| `experiments/` | Einzelne Testskripte, nicht Teil des Produktivbetriebs |
| `docs/` | Aktuelle Doku; abgeschlossene Analysen und Protokolle liegen in `docs/archive/` |

## Häufige Befehle

```bash
make contract   # OpenAPI-Vertrag schreiben und prüfen
make generate   # Clients aus dem Vertrag erzeugen
make verify     # Vertrag gegen den Code prüfen

cd web && npm run dev     # Frontend lokal starten (Port 3000)
```

## Deployment

Der Server zieht `main` automatisch (systemd-Timer `cardyssey-deploy.timer`).
**Alles, was auf `main` landet, geht live.** Änderungen daher über Pull Requests einspielen.
Details: `docs/NATIVE_SHOP_TINY_RELEASE.md`, `docs/TINY_CONTAINERS.md`.

## Geheimnisse

Zugangsdaten gehören in `.env`-Dateien auf dem Server, nie ins Repo. Vorlage: `web/.env.example`.
