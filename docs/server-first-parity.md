# Cardyssey server-first parity

## Zielbild

Cardyssey folgt für Fachlogik und persistente Nutzerdaten diesem Pfad:

`PostgreSQL -> Backend -> OpenAPI -> generierte Clients -> Web / Android`

Web und Android sind dünne Clients. Gerätelogik wie CameraX/ML Kit darf lokal bleiben, fachliche Regeln sollen nicht parallel in mehreren Clients gepflegt werden.

## Aktueller zentraler Stand

Das Backend ist bereits die zentrale Quelle für:

- Auth und Session-Lifecycle
- Profil und Avatar
- Collection
- Friends und Friend Requests
- Privacy
- Showcase
- Wishlist
- Selling
- Marketplace
- Offers
- Kartenkatalog, Sets und Card Recognition

Web und Android besitzen für diese Bereiche bereits Oberflächen bzw. Repositories. Der Haupt-Restbestand ist daher keine fehlende Feature-Liste, sondern das Abbauen älterer Client-seitiger Parallel-Logik.

## Android-Migrationsbestand

Android verwendet für die zentralen Community-/Account-Funktionen zunehmend den generierten OpenAPI-Client. Neue handgeschriebene HTTP-/JSON-Wege sollen nicht mehr hinzukommen.

Gerätenahe Scanner-/OCR-Verarbeitung bleibt lokal. Lokale Katalog-Caches und Matching-Hilfen dürfen für Latenz/Offline-Verhalten bestehen, fachliche Karten- und Variantenregeln sollen jedoch aus dem Backend kommen.

## Wichtigster Restbestand: Pricing

Android enthält derzeit noch aktive lokale Preisprovider und Resolver. Web berechnet Zustandsfaktoren und Positionswerte ebenfalls clientseitig. Das ist der wichtigste verbliebene Architekturbruch.

Die Migration erfolgt ohne Datenverlust und ohne einen funktionierenden Preisweg vorzeitig abzuschalten:

1. Preisbeschaffung, Normalisierung und Zustandsregeln serverseitig bereitstellen.
2. Vertrag in OpenAPI abbilden.
3. Clients neu generieren.
4. Web auf Serverwerte umstellen.
5. Android auf Serverwerte umstellen.
6. Erst danach alte lokale Provider-/Resolver-Komponenten und APK-seitige Provider-Konfiguration entfernen.

Es gilt weiterhin: lieber kein Preis als ein falscher Preis; Variantenidentität darf nicht über einen Preis erraten werden.

## Daten- und Betriebsgrenzen

Bei dieser Migration werden weder Android-App-Daten gelöscht noch PostgreSQL zurückgesetzt oder neu initialisiert. Collections werden nicht überschrieben. Tiny-Netzwerk/Cloudflare-Konfiguration bleibt unverändert.

Änderungen an zentraler Fachlogik beginnen im Platform-Repository und werden über den bestehenden Tiny-Autodeploy ausgerollt; Web und Android werden anschließend nur angebunden.
