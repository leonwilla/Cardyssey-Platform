import {
  BrandMark,
} from "@/components/BrandMark";

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{
    error?: string;
  }>;
}) {
  const params = await searchParams;

  const error =
    params.error
      ? params.error ===
        "email_already_registered"
        ? "Diese E-Mail ist bereits registriert."
        : params.error ===
          "server_unavailable"
          ? "Server momentan nicht erreichbar. Bitte versuche es gleich erneut."
          : "Registrierung fehlgeschlagen."
      : null;

  return (
    <main className="authPage">
      <div className="authGlow" />

      <section className="authCard">
        <div className="authBrand">
          <BrandMark />
          <strong>Cardyssey</strong>
        </div>

        <span className="eyebrowText">
          Ein Account. Überall.
        </span>

        <h1>
          Deine Reise beginnt hier
        </h1>

        <p>
          Die öffentliche Registrierung startet nach der privaten Testphase.
        </p>

        <div className="authTabs">
          <a href="/login">
            Anmelden
          </a>

          <a
            className="active"
            href="/register"
          >
            Registrieren
          </a>
        </div>

        <div className="statusPanel" role="status">
          <strong>Registrierung während der privaten Testphase geschlossen.</strong>
          <p>Cardyssey ist aktuell nur für freigeschaltete Testaccounts verfügbar. Sobald die öffentliche Registrierung startet, kannst du hier deinen Account erstellen.</p>
          <a className="primaryButton inline" href="/login">Zur Anmeldung</a>
        </div>
      </section>
    </main>
  );
}
