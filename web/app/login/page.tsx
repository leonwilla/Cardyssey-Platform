"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  BrandMark,
} from "@/components/BrandMark";

export default function LoginPage() {
  const [shopReturnTo,setShopReturnTo]=useState("");
  const [error, setError] =
    useState<string | null>(null);
  const [passwordChanged, setPasswordChanged] = useState(false);

  useEffect(() => {
    setPasswordChanged(new URLSearchParams(window.location.search).get("password_changed") === "1");
    const code =
      new URLSearchParams(
        window.location.search
      ).get("error");

    const next = new URLSearchParams(window.location.search).get("returnTo");
    if (next) {try {const url=new URL(next);if(url.protocol==="https:"&&url.hostname==="shop.cardyssey.de"&&!url.port)setShopReturnTo(url.toString())}catch{}}
    setError(
      code && code !== "access_restricted"
        ? code === "invalid_credentials"
          ? "E-Mail oder Passwort ist falsch."
          : code === "server_unavailable"
            ? "Server momentan nicht erreichbar. Bitte versuche es gleich erneut."
            : "Anmeldung fehlgeschlagen."
        : null
    );
  }, []);

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
          Willkommen zurück
        </h1>

        <p>
          Deine Sammlung, Freunde und
          Marktdaten auf allen Geräten.
        </p>

        <div className="authTabs">
          <a
            className="active"
            href="/login"
          >
            Anmelden
          </a>

          <a href="/register">
            Registrieren
          </a>
        </div>

        {passwordChanged && (
          <p className="authSuccess" role="status">Passwort erfolgreich geändert. Bitte melde dich erneut an.</p>
        )}

        <form
          className="authForm"
          method="post"
          action="/api/auth/login"
        >
          {shopReturnTo && <input type="hidden" name="returnTo" value={shopReturnTo}/>}
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
              autoComplete="current-password"
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
            Anmelden
          </button>
        </form>

        <small className="authSecurity">
          Deine Sitzung wird sicher über
          HttpOnly-Cookies gespeichert.
        </small>
      </section>
    </main>
  );
}
