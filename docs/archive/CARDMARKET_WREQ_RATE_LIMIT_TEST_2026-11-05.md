# Cardmarket – unabhängiger schneller HTTP-Test, 5. November 2026

## Prüfstand und tatsächliche Ergebnisse

- Grundlage: Nutzerdatei `pricecharting_cf.py` mit Chrome/CDP zur einmaligen Sitzungsherstellung und `wreq` HTTP-Client. `experiments/cardmarket_cf_exact_transport.py` ändert die Ziel-Domain und den Sitzungsdateinamen; sonst bleibt die Transportlogik gleich.
- **Erster Lauf:** Browser-Sitzung nach 5,2 s, Cardmarket-Startseite danach via `wreq` HTTP 200 (125.941 Bytes); Gesamtlauf 8,27 s.
- **Erster Produktversuch:** Lucario MEP 095, Produkt-ID 895610, HTTP 200, 265.182 Bytes in 0,57 s.
- **Zehn Produktseiten, nur 2,5 s Pause:** 9× HTTP 200 mit passender Produkt-ID und erkennbaren Angebots-/Preismarkups, 10. Abruf HTTP 429 mit Cloudflare-Challenge. Durchschnitt der neun erfolgreichen Antwortzeiten rund 0,64 s. Die erfolgreichen Seiten enthalten *nicht automatisch* bestätigte DE/NM-/Sonderdruckpreise.
- **Zweiter Lauf mit mindestens 12 s Pause:** erste Anfrage unmittelbar HTTP 429. Das weist auf eine weiterhin wirksame Begrenzung hin, ohne zu belegen, welche genaue Ursache sie hat. Ein bereits aktiver Windows-Collector könnte zuvor zur Last beigetragen haben, war zum Zeitpunkt des erneuten Versuchs aber vollständig abgeschlossen (1.460/1.460).
- Der zweite Lauf wurde nach dem 429 **ohne weitere Wiederholungen beendet**. Ein 30-minütiger Mindest-Cooldown wurde in `/tmp/cardmarket_http_cooldown.json` gespeichert (im selben Ordner wie die Ergebnisdatei).

## Schutzlogik

`experiments/cardmarket_safe_http_probe.py` ist ein **reines Diagnoseprogramm**, kein produktiver Preisimport:
- überprüft https-Host und Produktsuchpfad, Produkt-ID im HTML und HTTP-Status;
- erzwingt ein Mindestintervall von 10 s, standardmäßig 12 s (auch wenn die reine HTTP-Antwort unter einer Sekunde bleibt);
- stoppt beim ersten HTTP 429/403/Cloudflare-Challenge, respektiert numerisches `Retry-After` sofern länger, und legt einen Cooldown-Marker an;
- nutzt ein exklusives Prozess-Lock, damit zwei Instanzen des Python-Tests nicht gleichzeitig laufen;
- veröffentlicht **keine** unbestätigten Preise, filtert **nicht** automatisch auf die exakte Sprache/Zustand/Druckvariante;
- **keine** automatische Neulösung der Challenge nach einer Sperre, keine Proxy-/IP-Rotation, keine erhöhten Raten nach Fehlversuchen.

### Betrieb

Im Tiny über eine separate virtuelle Umgebung (nicht während eines anderen Cardmarket-Collectors) starten:

```bash
cd ~/cardshop
.venv-cardmarket-cf-test/bin/python experiments/cardmarket_safe_http_probe.py \
  --input /tmp/cardyssey-cm-test-10-input.json \
  --output /tmp/cardyssey-cm-safe-test-results.jsonl \
  --min-interval 12
```

Die vorhandene WSL-Chrome-Installation nutzt bei Bedarf `LD_LIBRARY_PATH=/home/tv/.local/opt/cardyssey-chrome/deps/usr/lib/x86_64-linux-gnu`. Bei einem Cooldown keine sofortigen Wiederholungen. Produktionsseitig bleiben der offizielle Cardmarket-Preisguide und der schon bestehende Windows-Collector die verlässlichen Pfade; der HTTP-Test ersetzt sie nicht.

## Entscheidung

Die reine Seitenantwort ist schnell, aber das 9/10→429-Ergebnis und die anschließende Sofort-Sperre zeigen, dass sich daraus *keine* 20 Karten pro Sekunde und keine skalierbare Gesamtpreisaktualisierung ableiten lassen. Eine größere Geschwindigkeitssteigerung erfordert sichere Katalogzuordnung und weniger Seitenabrufe; die Filter-/Variantenprüfung bleibt eigenständig.
