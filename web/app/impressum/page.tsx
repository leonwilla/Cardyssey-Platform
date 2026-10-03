import Link from "next/link";
import { legalOperator } from "@/lib/legal";

export const metadata = {
  title: "Impressum | Cardyssey",
};

export default function ImpressumPage() {
  const operator = legalOperator();

  return (
    <main className="legalPage">
      <div className="legalShell">
        <Link href="/" className="legalBack">
          ← Cardyssey
        </Link>

        <span className="legalEyebrow">Rechtliches</span>
        <h1>Impressum</h1>

        {!operator.complete && (
          <div className="legalWarning">
            Die Betreiberanschrift und Kontakt-E-Mail müssen vor der
            öffentlichen Veröffentlichung noch über die LEGAL_* Variablen
            im Deployment ergänzt werden.
          </div>
        )}

        <section>
          <h2>Angaben gemäß § 5 DDG</h2>
          <address>
            <strong>{operator.name}</strong>
            {operator.street && <span>{operator.street}</span>}
            {operator.postalCity && <span>{operator.postalCity}</span>}
            <span>{operator.country}</span>
          </address>
        </section>

        <section>
          <h2>Kontakt</h2>
          {operator.email ? (
            <a href={`mailto:${operator.email}`}>
              {operator.email}
            </a>
          ) : (
            <p>Kontakt-E-Mail wird im Deployment hinterlegt.</p>
          )}
        </section>

        <section>
          <h2>Verantwortung für Inhalte</h2>
          <p>
            Cardyssey stellt Funktionen zur Verwaltung von
            Sammelkarten, Community-Kommunikation, Wishlist,
            Marketplace und verwandten Sammlerfunktionen bereit.
            Für nutzergenerierte Inhalte bleiben die jeweiligen
            Nutzer verantwortlich, soweit gesetzlich vorgesehen.
          </p>
        </section>

        <section>
          <h2>Hinweis zu Marken</h2>
          <p>
            Pokémon und zugehörige Marken, Namen und Abbildungen
            gehören ihren jeweiligen Rechteinhabern. Cardyssey ist
            kein offizielles Produkt von The Pokémon Company,
            Nintendo, Game Freak oder Creatures.
          </p>
        </section>

        <div className="legalLinks">
          <Link href="/datenschutz">Datenschutz</Link>
          <Link href="/">Startseite</Link>
        </div>
      </div>
    </main>
  );
}
