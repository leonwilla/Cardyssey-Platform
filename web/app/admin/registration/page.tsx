"use client";

import {
  useEffect,
  useState,
} from "react";
import {
  useRouter,
} from "next/navigation";

import {
  AppShell,
} from "@/components/AppShell";
import type { User } from "@/lib/types";

type RegistrationSettings = {
  enabled: boolean;
};

export default function RegistrationAdminPage() {
  const router = useRouter();

  const [user, setUser] =
    useState<User | null>(null);
  const [settings, setSettings] =
    useState<RegistrationSettings | null>(null);
  const [loading, setLoading] =
    useState(true);
  const [saving, setSaving] =
    useState(false);
  const [message, setMessage] =
    useState<string | null>(null);

  useEffect(() => {
    void initialize();
  }, []);

  async function initialize() {
    setLoading(true);
    setMessage(null);

    try {
      const meResponse =
        await fetch("/api/auth/me", {
          cache: "no-store",
        });

      if (meResponse.status === 401) {
        router.replace("/login");
        return;
      }

      if (!meResponse.ok) {
        throw new Error(
          "Account konnte nicht geladen werden."
        );
      }

      const me =
        await meResponse.json() as User;

      if (
        me.role !== "FOUNDER" &&
        me.canFounder !== true
      ) {
        router.replace("/admin");
        return;
      }

      setUser(me);

      const response =
        await fetch(
          "/api/admin/registration",
          { cache: "no-store" }
        );

      if (!response.ok) {
        throw new Error(
          "Registrierungsstatus konnte nicht geladen werden."
        );
      }

      setSettings(
        await response.json() as RegistrationSettings
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Registrierungsstatus konnte nicht geladen werden."
      );
    } finally {
      setLoading(false);
    }
  }

  async function setRegistrationEnabled(
    enabled: boolean
  ) {
    setSaving(true);
    setMessage(null);

    try {
      const response =
        await fetch(
          "/api/admin/registration",
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ enabled }),
          }
        );

      if (!response.ok) {
        throw new Error(
          "Registrierung konnte nicht geändert werden."
        );
      }

      const updated =
        await response.json() as RegistrationSettings;

      setSettings(updated);
      setMessage(
        updated.enabled
          ? "Registrierungen sind jetzt geöffnet."
          : "Registrierungen sind jetzt gesperrt."
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Registrierung konnte nicht geändert werden."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell
      active="/admin"
      user={user}
    >
      <section className="pageIntro">
        <div>
          <span className="eyebrowText">
            Founder
          </span>
          <h1>Registrierung</h1>
          <p>
            Hier steuerst du, ob neue Cardyssey-Accounts angelegt
            werden dürfen. Bestehende Accounts und Logins bleiben
            davon unberührt.
          </p>
        </div>
      </section>

      {message && (
        <div className="statusPanel">
          {message}
        </div>
      )}

      <section className="sectionBlock">
        <div className="statusPanel">
          {loading ? (
            "Registrierungsstatus wird geladen …"
          ) : settings ? (
            <div
              style={{
                display: "grid",
                gap: "16px",
              }}
            >
              <div>
                <span className="eyebrowText">
                  Öffentliche Registrierung
                </span>
                <h2 style={{ marginBottom: "6px" }}>
                  {settings.enabled
                    ? "● Geöffnet"
                    : "● Gesperrt"}
                </h2>
                <p className="muted">
                  {settings.enabled
                    ? "Neue Nutzer können sich aktuell selbst registrieren."
                    : "Neue Selbstregistrierungen werden aktuell serverseitig blockiert."}
                </p>
              </div>

              <button
                type="button"
                className="ghostButton"
                disabled={saving}
                onClick={() =>
                  void setRegistrationEnabled(
                    !settings.enabled
                  )
                }
                style={{
                  width: "fit-content",
                  borderColor: settings.enabled
                    ? "rgba(255,90,120,.45)"
                    : "rgba(96,230,180,.45)",
                }}
              >
                {saving
                  ? "Wird gespeichert …"
                  : settings.enabled
                    ? "Registrierungen sperren"
                    : "Registrierungen öffnen"}
              </button>

              <small className="muted">
                Die Sperre sitzt im Backend. Sie gilt deshalb für
                Web-App und Android-App gleichermaßen.
              </small>
            </div>
          ) : (
            "Kein Registrierungsstatus verfügbar."
          )}
        </div>
      </section>
    </AppShell>
  );
}
