"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  BrandMark,
} from "@/components/BrandMark";

export default function LoginPage() {
  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    const code =
      new URLSearchParams(
        window.location.search
      ).get("error");

    setError(
      code
        ? code === "invalid_credentials"
          ? "E-Mail oder Passwort ist falsch."
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

        <form
          className="authForm"
          method="post"
          action="/api/auth/login"
        >
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
