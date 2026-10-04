import Link from "next/link";
import { legalOperator } from "@/lib/legal";

export const metadata = {
  title: "Datenschutz | Cardyssey",
};

export default function DatenschutzPage() {
  const operator = legalOperator();

  return (
    <main className="legalPage">
      <div className="legalShell">
        <Link href="/" className="legalBack">
          ← Cardyssey
        </Link>

        <span className="legalEyebrow">Rechtliches</span>
        <h1>Datenschutzerklärung</h1>

        <div className="legalWarning">
          Die Hosting- und Infrastrukturangaben werden vor der
          öffentlichen Veröffentlichung noch anhand des produktiven
          Cardyssey-Setups ergänzt.
        </div>

        <section>
          <h2>1. Verantwortlicher</h2>
          <p>
            Verantwortlich für Cardyssey ist {operator.name},
            {operator.street && <> {operator.street},</>}
            {operator.postalCity && <> {operator.postalCity},</>}
            {" "}{operator.country}. Kontakt:{" "}
            <a href={`mailto:${operator.email}`}>{operator.email}</a>.
          </p>
        </section>

        <section>
          <h2>2. Welche Daten verarbeitet werden</h2>
          <p>
            Cardyssey verarbeitet insbesondere Accountdaten
            (E-Mail-Adresse, Anzeigename und Authentifizierungsdaten),
            Sammlungs-, Wishlist-, Showcase- und Marketplace-Daten,
            Freundschaften, Chat- und Moderationsdaten sowie
            technische Protokolldaten, die für Betrieb, Sicherheit
            und Fehlerdiagnose erforderlich sind.
          </p>
        </section>

        <section>
          <h2>3. Zweck und Rechtsgrundlagen</h2>
          <p>
            Die Verarbeitung erfolgt zur Bereitstellung des
            Cardyssey-Accounts und der vom Nutzer angeforderten
            Funktionen, zur Synchronisierung zwischen Web und
            Android, zur Missbrauchs- und Sicherheitsprävention sowie
            zur Bearbeitung von Support- und Moderationsfällen.
            Je nach Verarbeitung kommen insbesondere Art. 6 Abs. 1
            lit. b, lit. c und lit. f DSGVO in Betracht.
          </p>
        </section>

        <section>
          <h2>4. Authentifizierung und lokale Speicherung</h2>
          <p>
            Für die Anmeldung werden Zugriffs- und
            Aktualisierungstoken verwendet. Im Web werden dafür
            geschützte Cookies eingesetzt. In der Android-App werden
            Sitzungsinformationen im geschützten App-Speicher
            verwaltet. Passwörter werden serverseitig nicht im
            Klartext gespeichert.
          </p>
        </section>

        <section>
          <h2>5. Community, Chats und Moderation</h2>
          <p>
            Nachrichten und von Nutzern geteilte Karten-, Set- oder
            Profildaten werden gespeichert, damit die
            Kommunikationsfunktionen bereitgestellt werden können.
            Meldungen, Sperren und Moderationsmaßnahmen können zur
            Sicherheit der Community protokolliert werden.
          </p>
        </section>

        <section>
          <h2>6. Push-Benachrichtigungen</h2>
          <p>
            Wenn Push-Benachrichtigungen aktiviert werden, nutzt die
            Android-App Firebase Cloud Messaging von Google. Dabei
            wird ein gerätebezogenes Push-Token verarbeitet und dem
            eingeloggten Cardyssey-Account zugeordnet. Nutzer können
            Benachrichtigungen über die Systemeinstellungen ihres
            Geräts deaktivieren.
          </p>
        </section>

        <section>
          <h2>7. Karten-, Bild- und Preisdaten</h2>
          <p>
            Zur Bereitstellung des Kartenkatalogs, von Kartenbildern
            und Marktinformationen können Daten aus angebundenen
            Katalog- und Preisdiensten verarbeitet und serverseitig
            zwischengespeichert werden. Dabei werden für diese
            Abrufe grundsätzlich keine privaten Chat-Inhalte an
            Karten- oder Preisdienste übertragen.
          </p>
        </section>

        <section>
          <h2>8. Speicherdauer</h2>
          <p>
            Personenbezogene Daten werden nur so lange gespeichert,
            wie sie für die jeweiligen Funktionen, gesetzliche
            Pflichten, Missbrauchsprävention oder die Durchsetzung
            und Abwehr von Ansprüchen erforderlich sind.
            Nutzer können ihren Cardyssey-Account in den
            Account-Einstellungen selbst dauerhaft löschen.
            Accountbezogene Daten und unmittelbar verknüpfte Inhalte
            werden dabei entfernt, soweit keine gesetzlichen
            Aufbewahrungspflichten oder zwingenden berechtigten
            Gründe einer Löschung entgegenstehen.
          </p>
        </section>

        <section>
          <h2>9. Rechte betroffener Personen</h2>
          <p>
            Betroffene Personen haben im Rahmen der gesetzlichen
            Voraussetzungen insbesondere Rechte auf Auskunft,
            Berichtigung, Löschung, Einschränkung der Verarbeitung,
            Datenübertragbarkeit und Widerspruch. Außerdem besteht
            ein Beschwerderecht bei einer zuständigen
            Datenschutzaufsichtsbehörde.
          </p>
        </section>

        <section>
          <h2>10. Sicherheit</h2>
          <p>
            Cardyssey setzt technische und organisatorische
            Maßnahmen ein, darunter verschlüsselte Übertragung,
            Zugriffskontrollen, abgesicherte Authentifizierung,
            restriktive Browser-Sicherheitsheader und getrennte
            Berechtigungen für administrative Funktionen.
          </p>
        </section>

        <section>
          <h2>11. Änderungen</h2>
          <p>
            Diese Datenschutzerklärung wird angepasst, wenn sich
            Funktionen, Anbieter oder rechtliche Anforderungen
            ändern.
          </p>
        </section>

        <div className="legalLinks">
          <Link href="/impressum">Impressum</Link>
          <Link href="/">Startseite</Link>
        </div>
      </div>
    </main>
  );
}
