"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

export function AccountSecurityPanel() {
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [visible, setVisible] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    if (newPassword.length < 12 || newPassword.length > 128) {
      setMessage("Das neue Passwort muss zwischen 12 und 128 Zeichen lang sein.");
      return;
    }
    if (newPassword !== confirmation) {
      setMessage("Die beiden neuen Passwörter stimmen nicht überein.");
      return;
    }
    if (currentPassword === newPassword) {
      setMessage("Das neue Passwort muss sich vom bisherigen unterscheiden.");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch("/api/auth/password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ currentPassword, newPassword }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({})) as { error?: string };
        if (data.error === "incorrect_current_password") {
          setMessage("Das bisherige Passwort ist nicht korrekt.");
        } else if (response.status === 429) {
          setMessage("Zu viele Versuche. Bitte versuche es später erneut.");
        } else if (response.status === 401) {
          setMessage("Deine Sitzung ist abgelaufen. Bitte melde dich erneut an.");
        } else if (data.error === "invalid_password") {
          setMessage("Das neue Passwort muss 12 bis 128 Zeichen lang und anders sein.");
        } else {
          setMessage("Passwort konnte nicht geändert werden. Bitte erneut versuchen.");
        }
        return;
      }
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
      router.replace("/login?password_changed=1");
      router.refresh();
    } catch {
      setMessage("Verbindung fehlgeschlagen. Bitte erneut versuchen.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="accountSecurityPanel" aria-labelledby="securityTitle">
      <span className="eyebrowText">Konto &amp; Sicherheit</span>
      <h2 id="securityTitle">Passwort ändern</h2>
      <p className="muted">
        Zum Schutz deines Kontos bestätigst du dein bisheriges Passwort.
        Danach werden vorhandene Anmeldungen spätestens beim Ablauf ihres Zugangstokens ungültig.
      </p>
      <form onSubmit={changePassword} className="accountSecurityForm">
        <label className="editorField">
          <span>Aktuelles Passwort</span>
          <input
            type={visible ? "text" : "password"}
            autoComplete="current-password"
            required
            minLength={1}
            maxLength={128}
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
          />
        </label>
        <label className="editorField">
          <span>Neues Passwort</span>
          <input
            type={visible ? "text" : "password"}
            autoComplete="new-password"
            required
            minLength={12}
            maxLength={128}
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
          />
          <small>Mindestens 12 Zeichen, gerne eine längere Passphrase.</small>
        </label>
        <label className="editorField">
          <span>Neues Passwort wiederholen</span>
          <input
            type={visible ? "text" : "password"}
            autoComplete="new-password"
            required
            minLength={12}
            maxLength={128}
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
          />
        </label>
        <label className="accountSecurityReveal">
          <input type="checkbox" checked={visible} onChange={(event) => setVisible(event.target.checked)} />
          Passwörter anzeigen
        </label>
        {message && <p className="accountSecurityMessage" role="alert">{message}</p>}
        <button className="primaryButton" type="submit" disabled={saving}>
          {saving ? "Wird gespeichert …" : "Passwort sicher ändern"}
        </button>
      </form>
      <p className="accountSecurityFootnote">
        Danach musst du dich auf der Webseite und in der App erneut anmelden.
      </p>
    </section>
  );
}
