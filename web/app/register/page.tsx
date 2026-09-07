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
          Erstelle deinen zentralen
          Cardyssey-Account.
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

        <form
          className="authForm"
          method="post"
          action="/api/auth/register"
        >
          <label>
            Anzeigename
            <input
              name="displayName"
              required
              maxLength={100}
              autoComplete="name"
            />
          </label>

          <label>
            E-Mail
            <input
              type="email"
              name="email"
              required
              autoComplete="email"
            />
          </label>

          <label>
            Passwort
            <input
              type="password"
              name="password"
              required
              minLength={12}
              autoComplete="new-password"
            />
          </label>

          {error && (
            <div className="authError">
              {error}
            </div>
          )}

          <button
            className="primaryButton authSubmit"
            type="submit"
          >
            Account erstellen
          </button>
        </form>
      </section>
    </main>
  );
}
