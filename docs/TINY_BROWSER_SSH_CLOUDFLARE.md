# Browser-SSH zum Lenovo Tiny mit Cloudflare Access

Status: **nur vorbereitet; nicht aktiv / nicht deployed**.

## Ziel

Eine private Browser-Konsole unter `terminal.cardyssey.de`, geschützt durch Cloudflare Access. Kein offener Router-/Firewall-Inbound-Port, keine VPN- oder SSH-Software auf dem zugreifenden Browser-Gerät. Firmenrichtlinien sind zu beachten; Netzwerkblockaden nicht umgehen.

Offizielle Dokumentation:
- https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/use-cases/ssh/ssh-browser-rendering/
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/non-http/browser-rendering/

## Voraussetzungen und Sicherheitsentscheidungen

1. Tiny muss dauerhaft laufen; WSL2 Ubuntu mit SSH muss nach Windows-Neustart automatisch gestartet werden oder der Tunnel ist offline.
2. `cloudflared` bevorzugt **in derselben WSL2-Ubuntu-Umgebung wie der SSH-Server** starten. Dann ist der Tunnel-Origin `ssh://localhost:22`. Falls Windows den Tunnel ausführt und WSL2 auf Windows-Port 2222 weiterleitet, explizit `ssh://127.0.0.1:2222` verwenden. **Niemals blind beide verbinden.**
3. Keine SSH-Ports am Router freigeben.
4. Vor Veröffentlichung Access-Anwendung und **Allow**-Policy für eine exakt definierte Identität einrichten; keine Bypass-Policies. Cloudflare Access mit MFA-fähigem IdP benutzen.
5. Cloudflare Browser-rendered SSH erwartet laut aktueller Dokumentation, dass das **E-Mail-Präfix** des Access-Benutzers zum **Linux-Benutzernamen** passt. Bestehender Linux-Benutzer ist `tv`; die verwendete Access-Identität muss entsprechend passen oder nach dokumentierter Methode konfiguriert werden. **Nicht** vorschnell Linux-Benutzer umbenennen oder Passwörter lockern.
6. Nur Browser-SSH für administrative Sitzungen; keine öffentliche Shell, kein `ttyd`-Webterminal ohne Authentisierung. Unbedingt erfolgreichen unauthentifizierten Zugriffstest (muss abgewiesen werden) durchführen.
7. SSH-Passwortlogin deaktivieren **erst**, wenn browserbasiertes und alternatives Schlüssel-/Notfallverfahren geprüft sind. Root-Login deaktiviert lassen. Recovery über Tailscale/AnyDesk/Lokalzugang beibehalten.
8. Cloudflare-Tunnel-Token ist geheim und gehört **nicht** ins GitHub-Repo, in Screenshots oder ins Browserfrontend.

## Cloudflare-Konfiguration (später vor Ort)

1. Cloudflare Zero Trust öffnen: **Networks > Tunnels > Create tunnel**; Tunnelname `cardyssey-tiny-terminal`.
2. Vorgeschlagenen Linux-Connector (`cloudflared`) **in WSL2** installieren und mit vertraulichem Tunnel-Token starten; Dienst für Neustarts absichern.
3. Unter **Published application** die Domain `terminal.cardyssey.de` anlegen, Typ **SSH**, Ziel `localhost:22`, sofern Connector in Ubuntu läuft.
4. **Access controls > Applications > Add application > Self-hosted** für genau `terminal.cardyssey.de` erstellen.
5. Access-Policy: **Allow** nur konkret freigegebene Identität(en); MFA über IdP erzwingen, kurze Sitzungslaufzeit. Keine öffentlich erlaubenden Gruppen oder Bypass-Regeln.
6. Browser rendering in der SSH-Access-Anwendung aktivieren (**Allow access through browser-based RDP, SSH, or VNC sessions → SSH**).
7. Linux-User-Zuordnung (siehe Präfix-Regel), Authentisierung und SSH-Host-Key verifizieren.
8. Private Browserprobe, danach unauthentifizierte Probe und Wiederanlauf nach Neustart testen.

## Optional: lokaler Read-only-Preflight auf dem Tiny

```bash
set -eu
id
uname -a
command -v sshd || true
sudo systemctl status ssh --no-pager || true
ss -lnt | grep -E ':(22|2222)[[:space:]]' || true
command -v cloudflared || true
command -v tailscale || true
```

Keine neuen Shell-Dienste, Portweiterleitungen oder öffentlichen DNS-Routen durch dieses Dokument angelegt.

## Abschlusstests

- Zugriff aus einem erlaubten privaten Browser funktioniert nur nach Access-Anmeldung und tatsächlicher SSH-Authentisierung.
- Nicht zugelassene Identitäten werden vor dem Origin blockiert.
- Tunnel und SSH werden nach Reboot wieder erreichbar; keine Direktverbindung auf 22/2222 aus dem Internet.
- Cloudflare-Sitzung und Linux-Konto sind getrennt dokumentiert; Recovery funktioniert.
- Firmencomputer nur nutzen, soweit organisatorisch erlaubt. Bei Sperre nicht ausweichen oder umgehen.
