# Gemeldete Scannerfehler vom 28.09.2026

Diese Punkte sind noch zu beheben; die Katalog-Erweiterung ist kein bestätigter Scanner-Fix.

- [ ] Direkt nach APK-Update erscheint die Kameravorschau überhell und unscharf/verpixelt. Nach einem App-Neustart ist sie wieder normal. Kamera-Lifecycle, Autofokus und Belichtung bei erster Initialisierung prüfen.
- [ ] Englische Mega Chandelure ex, Pitch Black, 115/084 wird wiederholt falsch erkannt: Mega Pyroar ex 015 (Chaos Rising, 97 %) und Lampent 15 (Plasma Freeze, 100 %). OCR darf die führende 1 nicht verlieren; Nummer, Set, Kartenname und Bild müssen gemeinsam geprüft werden. Widersprüchliche Merkmale dürfen keine automatische Übernahme mit hoher Sicherheit auslösen.
- [ ] Manuelle Suche mit 115/084 findet nichts, obwohl die Namenssuche drei Varianten 038, 099 und 115 aus Pitch Black findet. Datenbestand ist hier vorhanden; Nummernparser und Filter prüfen.
- [ ] Nummernsuche soll 115/084, 115 084 und 115 akzeptieren. Bei alleiniger Nummer mehrere Sets als Auswahl zeigen. Zusammengeschriebene Eingaben wie 115084 nicht blind halbieren: Nummern und Setgrößen sind unterschiedlich lang.

Regression: dieselbe Karte bei normalem Licht mehrfach scannen und manuell über alle drei Eingaben finden. Falsche Treffer dürfen weder übernommen noch als 97–100 % sicher angezeigt werden.
