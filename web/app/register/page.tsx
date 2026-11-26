import {
  BrandMark,
} from "@/components/BrandMark";
import { AuthDeckSide } from "@/components/AuthDeckSide";
import { backendFetch } from "@/lib/server/cardyssey-api";
import "../auth-deck.css";

export const dynamic = "force-dynamic";

async function registrationsOpen(): Promise<boolean> {
  try {
    const response = await backendFetch(
      "/api/v1/auth/registration-status"
    );
    if (!response.ok) return false;
    const data = await response.json();
    return data?.enabled === true;
  } catch {
    return false;
  }
}

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{
    error?: string;
  }>;
}) {
  const params = await searchParams;
  const open = await registrationsOpen();

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
    <main className="authPage authDeck">
      <AuthDeckSide />

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

        {!open && (
          <p>
            Die öffentliche Registrierung startet nach der privaten Testphase.
          </p>
        )}

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

        {open ? (
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
            Passwort (mindestens 12 Zeichen)
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
        ) : (
        <div className="statusPanel" role="status">
          <strong>Registrierung während der privaten Testphase geschlossen.</strong>
          <p>Cardyssey ist aktuell nur für freigeschaltete Testaccounts verfügbar. Sobald die öffentliche Registrierung startet, kannst du hier deinen Account erstellen.</p>
          <a className="primaryButton inline" href="/login">Zur Anmeldung</a>
        </div>
        )}
      </section>
    </main>
  );
}
