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

import {
  PrivacySettingsPanel,
} from "@/components/PrivacySettingsPanel";

import {
  ShowcaseSettingsPanel,
} from "@/components/ShowcaseSettingsPanel";

import type {
  User,
} from "@/lib/types";

export default function AccountPage() {
  const router = useRouter();

  const [user, setUser] =
    useState<User | null>(null);

  const [displayName, setDisplayName] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [saving, setSaving] =
    useState(false);

  const [avatarSaving, setAvatarSaving] =
    useState(false);

  const [message, setMessage] =
    useState<string | null>(null);

  useEffect(() => {
    fetch(
      "/api/auth/me",
      { cache: "no-store" }
    )
      .then(async (response) => {
        if (response.status === 401) {
          router.replace("/login");
          return null;
        }

        if (!response.ok) {
          throw new Error(
            "Account konnte nicht geladen werden."
          );
        }

        return response.json();
      })
      .then((data: User | null) => {
        if (!data) return;

        setUser(data);
        setDisplayName(
          data.displayName ?? ""
        );
      })
      .finally(
        () => setLoading(false)
      );
  }, [router]);

  async function saveProfile() {
    setSaving(true);
    setMessage(null);

    try {
      const response =
        await fetch(
          "/api/auth/me",
          {
            method: "PUT",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              displayName,
            }),
          }
        );

      if (!response.ok) {
        throw new Error(
          "Profil konnte nicht gespeichert werden."
        );
      }

      const updated =
        await response.json() as User;

      setUser(updated);
      setDisplayName(
        updated.displayName ?? ""
      );

      setMessage(
        "Profil gespeichert."
      );

    } catch (e) {
      setMessage(
        e instanceof Error
          ? e.message
          : "Speichern fehlgeschlagen."
      );

    } finally {
      setSaving(false);
    }
  }

  async function uploadAvatar(
    file: File | null
  ) {
    if (!file) return;

    if (
      ![
        "image/jpeg",
        "image/png",
      ].includes(file.type)
    ) {
      setMessage(
        "Bitte JPG oder PNG auswählen."
      );
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setMessage(
        "Das Profilbild darf maximal 5 MB groß sein."
      );
      return;
    }

    setAvatarSaving(true);
    setMessage(null);

    try {
      const response =
        await fetch(
          "/api/auth/avatar",
          {
            method: "PUT",
            headers: {
              "Content-Type":
                "application/octet-stream",
            },
            body: file,
          }
        );

      if (!response.ok) {
        throw new Error(
          "Profilbild konnte nicht hochgeladen werden."
        );
      }

      const updated =
        await response.json() as User;

      setUser(updated);

      setMessage(
        "Profilbild gespeichert."
      );

    } catch (e) {
      setMessage(
        e instanceof Error
          ? e.message
          : "Upload fehlgeschlagen."
      );

    } finally {
      setAvatarSaving(false);
    }
  }

  async function deleteAvatar() {
    setAvatarSaving(true);
    setMessage(null);

    try {
      const response =
        await fetch(
          "/api/auth/avatar",
          {
            method: "DELETE",
          }
        );

      if (!response.ok) {
        throw new Error(
          "Profilbild konnte nicht gelöscht werden."
        );
      }

      const updated =
        await response.json() as User;

      setUser(updated);

      setMessage(
        "Profilbild entfernt."
      );

    } catch (e) {
      setMessage(
        e instanceof Error
          ? e.message
          : "Löschen fehlgeschlagen."
      );

    } finally {
      setAvatarSaving(false);
    }
  }

  async function copyFriendCode() {
    if (!user) return;

    await navigator.clipboard.writeText(
      user.friendCode
    );

    setMessage(
      "Cardyssey-ID kopiert."
    );
  }

  async function logout() {
    await fetch(
      "/api/auth/logout",
      { method: "POST" }
    );

    router.replace("/login");
    router.refresh();
  }

  return (
    <AppShell
      active="/account"
      user={user}
    >
      <section className="pageIntro">
        <div>
          <span className="eyebrowText">
            Account
          </span>

          <h1>
            Dein Cardyssey Account
          </h1>

          <p>
            Zentrale Identität für Web,
            Android und später den Shop.
          </p>
        </div>
      </section>

      {loading ? (
        <div className="statusPanel">
          Account wird geladen …
        </div>
      ) : user && (
        <>
          <section className="accountCard">
            <div className="avatar large">
              {user.avatarUrl ? (
                <img
                  src={user.avatarUrl}
                  alt="Profilbild"
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    borderRadius: "inherit",
                    display: "block",
                  }}
                />
              ) : (
                (user.displayName ||
                  user.email)
                  .charAt(0)
                  .toUpperCase()
              )}
            </div>

            <div>
              <h2>
                {user.displayName ||
                  "Cardyssey Collector"}
              </h2>

              <p className="muted">
                {user.email}
              </p>
            </div>
          </section>

          <section className="friendCodePanel">
            <div>
              <span className="eyebrowText">
                Deine Cardyssey-ID
              </span>

              <strong>
                {user.friendCode}
              </strong>

              <p>
                Über diese ID können dich
                später andere Sammler finden.
              </p>
            </div>

            <button
              className="ghostButton"
              onClick={copyFriendCode}
            >
              ID kopieren
            </button>
          </section>

          <section
            className="sectionBlock"
            style={{
              maxWidth: "650px",
            }}
          >
            <span className="eyebrowText">
              Android App
            </span>

            <h2>
              Cardyssey für Android
            </h2>

            <p className="muted">
              Lade hier immer die aktuellste
              Demo-Version der App herunter.
            </p>

            <a
              className="primaryButton inline"
              href="/downloads/cardyssey-latest.apk"
              download
            >
              Android App herunterladen
            </a>
          </section>

          <section
            className="sectionBlock"
            style={{
              maxWidth: "650px",
            }}
          >
            <span className="eyebrowText">
              Profil
            </span>

            <h2>
              Persönliche Daten
            </h2>

            <div className="editorField">
              <span>Profilbild</span>

              <input
                type="file"
                accept="image/jpeg,image/png"
                disabled={avatarSaving}
                onChange={
                  (event) => {
                    const file =
                      event.target.files?.[0]
                        ?? null;

                    uploadAvatar(file);

                    event.currentTarget.value =
                      "";
                  }
                }
              />

              {user.avatarUrl && (
                <button
                  type="button"
                  className="ghostButton"
                  style={{
                    marginTop: "10px",
                    alignSelf: "flex-start",
                  }}
                  disabled={avatarSaving}
                  onClick={deleteAvatar}
                >
                  Profilbild entfernen
                </button>
              )}

              {avatarSaving && (
                <span className="muted">
                  Profilbild wird verarbeitet …
                </span>
              )}
            </div>

            <label className="editorField">
              <span>Anzeigename</span>

              <input
                value={displayName}
                maxLength={100}
                placeholder="Dein Name"
                onChange={
                  (event) =>
                    setDisplayName(
                      event.target.value
                    )
                }
              />
            </label>

            <label className="editorField">
              <span>E-Mail</span>

              <input
                value={user.email}
                disabled
              />
            </label>

            {message && (
              <div className="statusPanel">
                {message}
              </div>
            )}

            <div
              className="editorActions"
              style={{
                marginTop: "20px",
              }}
            >
              <button
                className="ghostButton"
                onClick={logout}
              >
                Abmelden
              </button>

              <button
                className="primaryButton"
                onClick={saveProfile}
                disabled={saving}
              >
                {saving
                  ? "Speichert …"
                  : "Profil speichern"}
              </button>
            </div>
          </section>
          <ShowcaseSettingsPanel />

          <PrivacySettingsPanel />
        </>
      )}
    </AppShell>
  );
}
