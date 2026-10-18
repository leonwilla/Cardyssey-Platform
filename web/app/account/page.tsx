"use client";

import Image from "next/image";

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

import {
  AppearanceSettingsPanel,
} from "@/components/AppearanceSettingsPanel";

import type {
  User,
} from "@/lib/types";

import {
  ANDROID_APK_DOWNLOAD_URL,
  formatAndroidReleaseDate,
} from "@/lib/android-release";

import type {
  AndroidReleaseInfo,
} from "@/lib/android-release";

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

  const [deletingAccount, setDeletingAccount] =
    useState(false);

  const [avatarSaving, setAvatarSaving] =
    useState(false);

  const [message, setMessage] =
    useState<string | null>(null);

  const [accountTab, setAccountTab] =
    useState<
      "profile" |
      "showcase" |
      "privacy" |
      "appearance" |
      "app"
    >("profile");

  const [
    androidRelease,
    setAndroidRelease,
  ] =
    useState<AndroidReleaseInfo | null>(
      null
    );

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

  useEffect(() => {
    fetch(
      "/api/android/latest",
      {
        cache: "no-store",
      }
    )
      .then((response) => {
        if (!response.ok) {
          return null;
        }

        return response.json();
      })
      .then(
        (
          data:
            AndroidReleaseInfo | null
        ) => {
          if (data) {
            setAndroidRelease(data);
          }
        }
      )
      .catch(() => {
        // Download bleibt auch ohne
        // Versionsanzeige verfügbar.
      });
  }, []);


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

  async function deleteAccount() {
    const confirmed = window.confirm(
      "Account dauerhaft löschen? Sammlung, Wishlist, Showcase, Marketplace-Daten, Chats und weitere mit deinem Cardyssey-Account verknüpfte Daten werden gelöscht. Diese Aktion kann nicht rückgängig gemacht werden."
    );

    if (!confirmed) return;

    setDeletingAccount(true);
    setMessage(null);

    try {
      const response = await fetch(
        "/api/auth/me",
        { method: "DELETE" }
      );

      if (!response.ok) {
        throw new Error(
          "Account konnte nicht gelöscht werden."
        );
      }

      router.replace("/login");
      router.refresh();
    } catch (e) {
      setMessage(
        e instanceof Error
          ? e.message
          : "Account konnte nicht gelöscht werden."
      );
      setDeletingAccount(false);
    }
  }

  return (
    <AppShell
      active="/account"
      user={
        loading ? undefined : user
      }
    >
      <section className="pageIntro">
        <div>
          <span className="eyebrowText">
            Account
          </span>

          <h1>
            Dein Cardyssey-Konto
          </h1>

          <p>
            Profil, Cloud und Einstellungen
            auf Web und Android.
          </p>
        </div>
      </section>

      {loading ? (
        <div className="statusPanel">
          Account wird geladen …
        </div>
      ) : user && (
        <>
          <div className="accountSummaryGrid">
          <section className="accountCard">
            <div className="profileAvatarWrap">
              <label
                className="profileAvatarButton"
                title="Profilbild ändern"
              >
                <div className="avatar large">
                  {user.avatarUrl ? (
                    <Image width={96} height={96} unoptimized
                      src={user.avatarUrl}
                      alt="Profilbild"
                    />
                  ) : (
                    (user.displayName ||
                      user.email)
                      .charAt(0)
                      .toUpperCase()
                  )}
                </div>

                <span className="profileAvatarEdit">
                  Ändern
                </span>

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
              </label>
            </div>

            <div>
              <h2>
                {user.displayName ||
                  "Cardyssey Collector"}
              </h2>

              <p className="muted">
                {user.email}
              </p>

              {user.avatarUrl && (
                <button
                  type="button"
                  className="profileAvatarRemove"
                  disabled={avatarSaving}
                  onClick={deleteAvatar}
                >
                  Profilbild entfernen
                </button>
              )}
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
          </div>

          <section
            className="accountTabs"
            aria-label="Account Bereiche"
          >
            <button
              type="button"
              className={
                accountTab === "profile"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setAccountTab("profile")
              }
            >
              Profil
            </button>

            <button
              type="button"
              className={
                accountTab === "showcase"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setAccountTab("showcase")
              }
            >
              Showcase
            </button>

            <button
              type="button"
              className={
                accountTab === "privacy"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setAccountTab("privacy")
              }
            >
              Privatsphäre
            </button>

            <button
              type="button"
              className={
                accountTab === "appearance"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setAccountTab("appearance")
              }
            >
              Design
            </button>

            <button
              type="button"
              className={
                accountTab === "app"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setAccountTab("app")
              }
            >
              Android App
            </button>
          </section>

          {accountTab === "app" && (
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

            {androidRelease ? (
              <p className="androidReleaseMeta">
                Aktualisiert: {formatAndroidReleaseDate(
                  androidRelease.builtAt
                )}
              </p>
            ) : (
              <p className="androidReleaseMeta">
                Aktuelle Versionsinformationen
                werden geladen …
              </p>
            )}

            <a
              className="primaryButton inline"
              href={ANDROID_APK_DOWNLOAD_URL}
            >
              Android App herunterladen
            </a>
          </section>
          )}

          {accountTab === "profile" && (
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

            <div
              className="editorActions"
              style={{
                marginTop: "28px",
              }}
            >
              <button
                className="ghostButton"
                onClick={deleteAccount}
                disabled={deletingAccount}
              >
                {deletingAccount
                  ? "Account wird gelöscht …"
                  : "Account dauerhaft löschen"}
              </button>
            </div>
          </section>
          )}
          {accountTab === "showcase" && (
            <div className="accountTabPanel">
              <ShowcaseSettingsPanel />
            </div>
          )}

          {accountTab === "privacy" && (
            <div className="accountTabPanel">
              <PrivacySettingsPanel />
            </div>
          )}

          {accountTab === "appearance" && (
            <div className="accountTabPanel">
              <AppearanceSettingsPanel />
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}
