# Lenovo Tiny – automatischer Wiederanlauf nach Windows-Neustart

Konfiguration und Prüfergebnis: **11.11.2026**.

## Startreihenfolge

1. Windows startet. Beim Anmelden von Windows-Benutzer `TV` führt dessen
   Autostart-Ordner `Cardyssey-Desktop-Remote.cmd` aus. Dieser startet WSL2
   Ubuntu und fordert `systemctl --user start cardyssey-desktop-remote.service`
   an. Die Konfiguration liegt zusätzlich versioniert unter `ops/windows-startup/`.
2. WSL Ubuntu hat `systemd=true` in `/etc/wsl.conf` und für Benutzer `tv`
   `Linger=yes`. Der Benutzer-Dienst
   `~/.config/systemd/user/cardyssey-desktop-remote.service` ist aktiviert
   (Vorlage unter `ops/systemd-user/`). Er startet den vorhandenen
   `/home/tv/.local/bin/cardyssey-desktop-remote-start`, der per `flock`
   parallele Autostarts derselben Instanz verhindert.
3. Bricht der Remote-Prozess ab, versucht der WSL-Dienst nach **30 Sekunden**
   den Neustart. Die gespeicherte Autorisierung bleibt im Benutzerprofil,
   **keine Zugangsdaten werden im Repository gespeichert**.
4. Der Cloudflare-Tunnel, die GitHub-Runner, cron und die Next.js-Webapp
   laufen als Systemdienste; Docker hat für alle sechs Cardyssey-/Shop-Container
   `restart: unless-stopped`. Das Dashboard wird über HTTPS bereitgestellt.

**Wichtig:** Der Windows-Autostart-Ordner wird beim Anmelden des Benutzers
verarbeitet, nicht bereits garantiert vor der Windows-Anmeldung. Solange
kein anderes Windows-Programm WSL gestartet hat, ist vor der Anmeldung
auch der WSL-Dienst noch nicht erreichbar. Für einen vollständig kopflosen
Start *vor* der Anmeldung ist eine separate Windows-Startaufgabe mit den
passenden Berechtigungen erforderlich. Dies wurde nicht eingerichtet.

Die laufenden, vom Benutzer manuell gestarteten Remote-Prozesse wurden bei
Einrichtung **nicht** beendet. Der neue Dienst ist aktiviert, wird aber
erst beim nächsten regulären WSL-Start automatisch ausgeführt; ein zweiter
Windows-Neustart wurde nicht ausgelöst.

## Cardmarket nach einem Neustart

- Persistenter Edge-Login, Preis-CSV, Scan-Fortschritt und Guide-Baseline
  liegen unter `%LOCALAPPDATA%/Cardyssey/` und bleiben erhalten.
- `Cardmarket-Resume-Watchdog.ps1` darf nach einer Unterbrechung wegen eines
  geschlossenen Edge-Browsers **erst nach Ablauf der gesamten Sperrzeit**
  den normalen Launcher starten. Der Launcher prüft danach wieder
  Warm-up, `AVAILABLE`, `AUTHENTICATED` und Cloudflare-Challenge.
- **Keine** manuelle Wiederaufnahme während `BLOCKED`; bei `BLOCKED`
  bleibt die 240-minütige Schutzzeit unverändert. Die 10-Sekunden-Pause
  pro Anfrage und die 16er-Batches bleiben ebenfalls unverändert.
- Der Delta-Vergleich am 12.11.2026 bleibt im bestehenden Tiny-crontab
  und ändert keine Daten, wenn ein Browserlauf aktiv ist.

## Diagnose ohne Neustart

```bash
systemctl --user is-enabled cardyssey-desktop-remote.service
systemctl --user status cardyssey-desktop-remote.service --no-pager
loginctl show-user tv -p Linger
systemctl is-active cloudflared cardyssey-web cron
systemctl is-active cardyssey-deploy.timer
docker ps --format '{{.Names}} {{.Status}}'
python3 -m unittest discover -s scripts/cardmarket/tests -q
curl -I http://127.0.0.1:3000/login
```

Der Zustand `inactive` des **neuen** Remote-Dienstes ist bei der erstmaligen
Einrichtung beabsichtigt, solange bereits die manuelle Terminalverbindung
besteht. Ein tatsächlicher vollständig automatischer Start wird erst beim
nächsten Windows-/WSL-Neustart im Livebetrieb verifiziert.
