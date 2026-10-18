# Webapp in Docker: Vorbereitung für den Linux-Server

## Bisher
Die Next.js-Webapp läuft aktuell noch als eigener Node.js-Prozess auf dem Tiny unter Port 3000. API und PostgreSQL laufen in Docker.

## Neu vorbereitet
- Mehrstufiges Dockerfile für Next.js 16 mit Standalone-Ausgabe und eigener Node.js-Laufzeit.
- Docker Compose enthält jetzt den Webdienst im Profil `web-cutover`.
- Die Webapp verbindet sich containerintern über `http://api:8080` mit der API.
- Nach außen ist Port 3000 nur an `127.0.0.1` gebunden. Öffentlicher Zugriff erfolgt über die bestehende HTTPS-Weiterleitung.
- Das Profil muss ausdrücklich aktiviert werden. Reguläres `docker compose up -d` startet den neuen Webcontainer NICHT.

## Voraussetzungen vor der echten Umstellung
1. Datensicherung: PostgreSQL, Kartenbilder, Avatare, wichtige Serverkonfiguration extern sichern und Rücksicherung prüfen.
2. Auf dem Tiny ist Windows C: fast voll. Keinen neuen Container bauen, bevor ausreichend Speicher frei ist oder der neue Ubuntu-Server bereitsteht.
3. Prüfen, wie der alte Node-Webprozess gestartet und wieder gestartet wird.
4. Webapp-Konfiguration und erforderliche Geheimnisse sicher übertragen; niemals echte Schlüssel ins Git schreiben.
5. Erst auf dem neuen Server oder einer getrennten Testumgebung Web-Image bauen und Login, Sammlung, Scanner, Chat, Marketplace und Shop testen.
6. Den bisherigen Webprozess kontrolliert stoppen, dann das Docker-Webprofil starten und öffentliche HTTPS-Aufrufe prüfen.

## Befehle zur späteren Abnahme
Aus dem Verzeichnis `platform`:
- Konfiguration: `docker compose --profile web-cutover config --quiet`
- Build: `docker compose --profile web-cutover build web`
- Start nach Freigabe von Port 3000: `docker compose --profile web-cutover up -d web`
- Gesundheitsstatus: `docker compose --profile web-cutover ps web`

## Zurückrollen
`docker compose --profile web-cutover stop web` ausführen und danach den alten Node-Prozess wieder über die bekannte Startmethode aktivieren. PostgreSQL und API nicht zurücksetzen oder neu initialisieren.

## Aktueller Prüfstand
Compose-Konfiguration validiert, Profilisolierung geprüft, TypeScript-Prüfung bestanden. Docker-Image und produktive Umstellung absichtlich noch nicht durchgeführt (Speicherengpass).
