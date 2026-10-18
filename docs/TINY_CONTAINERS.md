# Cardyssey auf dem Lenovo Tiny

Diese Datei beschreibt die Produktionsdienste auf dem Tiny und trennt
Cardyssey von den anderen Projekten auf demselben Rechner.

## Cardyssey-Kern

| Container / Dienst | Pflicht | Aufgabe | Lokaler Port |
|---|---:|---|---:|
| `cardyssey-web` | Ja | Next.js-Web-App unter `cardyssey.de` | `127.0.0.1:3000` |
| `cardyssey-api` | Ja | Zentrale API für Web und Android | `127.0.0.1:8081` |
| `cardyssey-db` | Ja | PostgreSQL für Nutzer, Sammlung, Einstellungen, Chats und Preise | nur intern `5432` |
| `cardyssey-ebay-browser` | Nur für direkte eBay-Preise | Selenium/Chromium für den eBay-Collector | `127.0.0.1:7900` |
| Cloudflare Tunnel | Ja für öffentliche Domains | Leitet `cardyssey.de` und `api.cardyssey.de` an die lokalen Dienste | abhängig von der Installation |

Der Webcontainer ist nun im optionalen Docker-Compose-Profil `web-cutover` vorbereitet.
Ohne ausdrückliche Aktivierung dieses Profils läuft die Webapp weiterhin als
separater Node-Prozess. Einzelheiten und sichere Umstellung: `docs/web-docker-cutover.md`.

## Andere Projekte auf dem Tiny

Diese Container gehören nicht zum Cardyssey-Kern:

| Container | Projekt | Für Cardyssey erforderlich |
|---|---|---:|
| `cardshop-wordpress` | separater WordPress-Shop | Nein |
| `cardshop-db` | MariaDB des WordPress-Shops | Nein |
| `vinted-ingest` | Vinted-Bot | Nein |
| `palworld-server` | Palworld-Server | Nein |

Ein Fehler in diesen Diensten darf Cardyssey grundsätzlich nicht stoppen.
Gemeinsam belegen sie aber RAM und CPU auf demselben Tiny.

## Startreihenfolge

1. `cardyssey-db`
2. `cardyssey-ebay-browser` (wenn eBay-Preise benötigt werden)
3. `cardyssey-api`
4. `cardyssey-web`
5. Cloudflare Tunnel bzw. öffentliche Weiterleitung

Die API führt beim Start automatisch die Flyway-Datenbankmigrationen aus.

## Schneller Statuscheck

Aus dem Verzeichnis mit der Cardyssey-Compose-Datei:

```bash
docker compose config --services
docker compose ps
docker ps --filter "name=cardyssey"
```

Lokale Erreichbarkeit:

```bash
curl -i --max-time 5 http://127.0.0.1:3000/
curl -i --max-time 5 http://127.0.0.1:8081/api/v1/health
curl -I --max-time 5 http://127.0.0.1:7900/
```

Logs:

```bash
docker logs --tail=150 cardyssey-api
docker logs --tail=100 cardyssey-ebay-browser
docker logs --tail=150 cardyssey-web
```

Der letzte Befehl funktioniert erst, wenn die Web-App wirklich als
`cardyssey-web`-Container eingerichtet wurde.

## Web-App läuft noch außerhalb von Docker

Mit diesen Befehlen lässt sich der aktuelle Web-Prozess finden:

```bash
ss -ltnp | grep -E ':3000|:8080|:8081'
ps aux | grep -E 'next (start|dev)|npm (run )?start' | grep -v grep
systemctl --type=service --state=running | grep -Ei 'cardyssey|next|node|cloudflared'
pm2 list 2>/dev/null
```

Wenn auf `127.0.0.1:3000` kein Prozess lauscht, hat die öffentliche
Web-App kein funktionierendes Next.js-Origin.

## Ressourcen prüfen

Auf dem Tiny laufen mehrere speicherintensive Projekte gleichzeitig.
Insbesondere Palworld und der Selenium-Browser können viel RAM belegen.

```bash
docker stats --no-stream
free -h
```

Bei Speicherdruck zuerst prüfen, bevor Container blind neu gestartet oder
Limits erhöht werden.
