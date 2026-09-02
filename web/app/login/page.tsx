"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { BrandMark } from "@/components/BrandMark";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
    const payload = mode === "login"
      ? { email, password }
      : { email, password, displayName };

    try {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const message = data?.message || (data?.error === "invalid_credentials"
          ? "E-Mail oder Passwort ist falsch."
          : data?.error === "email_already_registered"
            ? "Diese E-Mail ist bereits registriert."
            : "Anmeldung fehlgeschlagen.");
        throw new Error(message);
      }

      router.replace("/collection");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Anmeldung fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="authPage">
      <div className="authGlow" />
      <section className="authCard">
        <div className="authBrand"><BrandMark /><strong>Cardyssey</strong></div>
        <span className="eyebrowText">Ein Account. Überall.</span>
        <h1>{mode === "login" ? "Willkommen zurück" : "Deine Reise beginnt hier"}</h1>
        <p>Sammlung, Sets und Marktwerte werden sicher mit deinem zentralen Cardyssey-Account synchronisiert.</p>

        <div className="authTabs">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Anmelden</button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Registrieren</button>
        </div>

        <form className="authForm" onSubmit={submit}>
          {mode === "register" && (
            <label>Anzeigename<input value={displayName} onChange={(e) => setDisplayName(e.target.value)} autoComplete="name" /></label>
          )}
          <label>E-Mail<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" /></label>
          <label>Passwort<input type="password" required minLength={12} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} /></label>

          {error && <div className="authError">{error}</div>}
          <button className="primaryButton authSubmit" disabled={busy}>{busy ? "Bitte warten …" : mode === "login" ? "Anmelden" : "Account erstellen"}</button>
        </form>

        <small className="authSecurity">Access- und Refresh-Tokens bleiben in HttpOnly-Cookies und sind nicht für JavaScript lesbar.</small>
      </section>
    </main>
  );
}
