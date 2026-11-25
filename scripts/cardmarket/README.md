# Cardyssey Cardmarket – Modulstruktur

Das Verzeichnis wurde am 11.11.2026 modularisiert. Alle produktiven
Daten/Queues/Browserprofile bleiben außerhalb des Git-Repositories im
Windows-Profil `%LOCALAPPDATA%\Cardyssey\CardmarketCollector`.

| Ordner | Inhalt |
| --- | --- |
| `core/` | Produktive Scanner, Windows-Launcher, Sessionprüfung, Feed- und Queue-Sync, Preis- und Variantengates, Delta-Workflow |
| `admin/` | Serverseitige Skripte für Next.js-Admin, Monitoring, Einzelprüfung und Druckvarianten-Review |
| `tests/` | Vollständige Python-/PowerShell-Regressionen und kanonischer Test-Datei-Locator |

**Hinweis zur Größe:** Es liegen mehr als 15 Dateien im Kern, weil der bestehende
Dauerbetrieb viele eigenständige Schritte enthält (DE/EN-Importe, Queue-Export,
Guide, Identitätsnachweis, Filterprüfung und 7-Tage-Delta). Ins Archiv wurden
nur Skripte verschoben, für die kein aktiver Cron- oder Wochenlauf-Aufruf
bekannt ist. Aktive `repair-`-, `reconcile-`- und `audit-`-Schritte bleiben im
`core/`, solange der Wochenlauf sie benötigt.

## Aufgeräumt am 25.11.2026

Alle Skripte, die von keinem Cron-Job, keiner Windows-Aufgabe, keinem Workflow,
keiner Admin-Seite und keinem anderen genutzten Skript aufgerufen wurden, sind
entfernt (Ordner `archive/` komplett, dazu u. a. `cardmarket_variant_resolver.py`,
`cardmarket-lightweight-search.ps1`, `apply-cardmarket-offline-review.py`).
Sie bleiben in der Git-Historie (Commit „Cardmarket aufgeräumt“). Behalten
wurden die Installations-Skripte für Windows (`Cardmarket-Collector-Install.ps1`,
`Install-Cardmarket-Telegram-Alerts.ps1`, `Cardmarket-Watchdog-Interval.ps1`).

## Live-Aufrufpfade

- Wochenlauf: `scripts/cardmarket/core/run-cardmarket-identity-weekly.py --apply`
- Browser-Skripte im Quellcode: `scripts/cardmarket/core/*.ps1`
- Windows-Installation: `python3 scripts/cardmarket/core/deploy-windows-modules.py --apply`.
  **Wichtig:** Die Installation kopiert ausschließlich Module/Regelkonfiguration
  in den bestehenden flachen `%LOCALAPPDATA%`-Collector. Sie verändert weder
  Browser-Cookies, Queue-CSV, Scanfortschritt noch Preise und verweigert
  Moduländerungen, wenn ein Windows-Scannerprozess läuft.
- Next.js API-Endpunkte: `scripts/cardmarket/admin/`.
- Vorhandene Windows-Aufgaben zeigen weiterhin auf die stabilen,
  installierten Dateinamen im Windows-Collector-Ordner.
- Cronjobs auf dem Tiny benutzen die neuen kanonischen Pfade. Die alte
  Crontab wurde unter `backups/cardmarket-migration-crontab-20261111.txt`
  lokal gesichert.

## Tests

```bash
python3 -m unittest discover -s scripts/cardmarket/tests
python3 scripts/cardmarket/core/cardmarket_delta_scan.py  # nur lesend
python3 scripts/cardmarket/core/deploy-windows-modules.py # nur lesend
```

Die Config-JSON verbleiben unverändert in `config/cardmarket-*` auf
Projekt-Root. Andere TCGs dürfen erst nach geprüftem Set-/Print-Crosswalk
aktiviert werden. Cloudflare-Schutzpausen, `BatchLimit=16`, 10-Sekunden-
Mindestabstand und Fail-Closed-Prüfungen bleiben bestehen.
