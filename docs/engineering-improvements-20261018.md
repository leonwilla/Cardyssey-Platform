# Cardyssey - Technische Verbesserungen (18.10.2026)

## Grundsatz
Bestehende Sprachen und Datenbank beibehalten: Kotlin/Compose Android, Kotlin/Ktor Backend, TypeScript/React/Next.js Web, Node.js, PostgreSQL 17, Python-Jobs. GitHub weiter fuer Versionsverwaltung und Test-APKs; Betrieb dauerhaft auf Ubuntu Server ohne Windows/WSL2.

## In Arbeit / Feature-Branch
- [x] Next.js-16-kompatible ESLint-Konfiguration und neuer TypeScript-Check eingerichtet.
- [x] Web-CI um  erweitert. Lokaler TypeScript-Check erfolgreich.
- [ ] Bestehende ESLint-Befunde beheben. Aktueller Stand (18.10.): 28 Fehler, 40 Warnungen nach Ausschluss von Fremdcode und generierten Dateien. Nicht als bestanden markieren.
- [ ] Nach Behebung der Befunde Lint als verbindlichen CI-Schritt aktivieren und Build/Smoke-Tests wiederholen.

## Geplante technische Arbeiten (noch nicht umgesetzt)
- [ ] Next.js-Webapp als eigenen Docker-Container in Compose integrieren, inklusive Port-/Prozess-Cutover.
- [ ] Node.js LTS-Version, React, TypeScript und andere Abhaengigkeiten gezielt aktualisieren und auf getestete Versionen festlegen.
- [ ] Gemeinsame fachliche Berechnungen und Karten-/Preisvariantenlogik im Kotlin-Backend vereinheitlichen (App-/Web-Paritaet).
- [ ] PostgreSQL, Katalogbilder, Avatare und Konfiguration vollstaendig und verschluesselt extern sichern; Restore testen.
- [ ] Sichere Releases mit Healthchecks, Rollback, getrennten Build-/Testjobs und ohne automatische Datenloeschung einrichten.
- [ ] Monitoring, Kapazitaet, TLS, Firewall und Admin-Zugriff auf neuem Linux-Server ausarbeiten.
- [ ] Speichernutzung am Tiny messen; nachhaltigen Ubuntu-Server mit benoetigter SSD-Kapazitaet planen und sorgfaeltig migrieren.
- [ ] Vor dem Start einer iOS-App SwiftUI vs. Kotlin Multiplatform vergleichen und macOS/Xcode-Buildzugang planen.

## Betriebshinweise
C: auf dem Windows-Tiny hatte am 18.10.2026 etwa 2,9 GB frei (99 % belegt). Keine grossen Container-Builds oder riskanten Produktivumstellungen vor Bereinigung/Datensicherung. Branch ist kein produktiver Release.
