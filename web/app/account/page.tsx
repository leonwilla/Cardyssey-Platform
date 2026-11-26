"use client";

import "../deck.css";
import "./account.css";

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

import FriendsPanel from "@/components/FriendsPanel";
import { AccountSecurityPanel } from "@/components/AccountSecurityPanel";

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

type AccountTab =
  | "profile"
  | "friends"
  | "security"
  | "showcase"
  | "privacy"
  | "appearance"
  | "app";

const ACCOUNT_TABS: { id: AccountTab; label: string; icon: string }[] = [
  { id: "profile", label: "Profil", icon: "◉" },
  { id: "friends", label: "Freunde", icon: "♢" },
  { id: "security", label: "Sicherheit", icon: "◈" },
  { id: "showcase", label: "Vitrine", icon: "★" },
  { id: "privacy", label: "Privatsphäre", icon: "◐" },
  { id: "appearance", label: "Design", icon: "✦" },
  { id: "app", label: "Android App", icon: "▣" },
];

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
    useState<AccountTab>("profile");

  const [
    androidRelease,
    setAndroidRelease,
  ] =
    useState<AndroidReleaseInfo | null>(
      null
    );

  useEffect(()=>{const t=new URLSearchParams(window.location.search).get("tab");if(t&&ACCOUNT_TABS.some(x=>x.id===t))setAccountTab(t as AccountTab)},[]);

  function openTab(tab: AccountTab) {
    setAccountTab(tab);
    setMessage(null);
    const url = new URL(window.location.href);
    if (tab === "profile") url.searchParams.delete("tab"); else url.searchParams.set("tab", tab);
    window.history.replaceState(null, "", url.toString());
  }

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
      "Account dauerhaft löschen? Sammlung, Wunschliste, Vitrine, Marktplatz-Daten, Chats und weitere mit deinem Cardyssey-Account verknüpfte Daten werden gelöscht. Diese Aktion kann nicht rückgängig gemacht werden."
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

  const initial = user ? (user.displayName || user.email).charAt(0).toUpperCase() : "";

  return (
    <AppShell
      active="/account"
      user={
        loading ? undefined : user
      }
    >
      <div className="dk ac">
        <section className="dk-deck ac-deck">
          <div className="dk-deckGrid">
            <div>
              <span className="dk-eyebrow">Account</span>
              <h1 className="dk-title">Dein Cardyssey-Konto</h1>
              <p className="dk-sub">Profil, Freunde, Sicherheit und Design. Alles gilt für Web und Android gleichermaßen.</p>
            </div>

            {user && (
              <div className="ac-pass">
                <div className="ac-passTop">
                  <span>Sammlerausweis</span>
                  {user.role === "FOUNDER" && <b>◆ Founder</b>}
                  {user.role === "ADMIN" && <b>Admin</b>}
                </div>
                <div className="ac-passMain">
                  <label className="ac-avatar" title="Profilbild ändern">
                    {user.avatarUrl ? <img src={user.avatarUrl} alt="Profilbild" /> : <span>{initial}</span>}
                    <i>{avatarSaving ? "…" : "Ändern"}</i>
                    <input
                      type="file"
                      accept="image/jpeg,image/png"
                      disabled={avatarSaving}
                      onChange={(event) => {
                        const file = event.target.files?.[0] ?? null;
                        uploadAvatar(file);
                        event.currentTarget.value = "";
                      }}
                    />
                  </label>
                  <div className="ac-passWho">
                    <strong>{user.displayName || "Cardyssey Collector"}</strong>
                    <small>{user.email}</small>
                    {user.avatarUrl && (
                      <button type="button" className="ac-link" disabled={avatarSaving} onClick={deleteAvatar}>Profilbild entfernen</button>
                    )}
                  </div>
                </div>
                <div className="ac-passId">
                  <div>
                    <small>Cardyssey-ID</small>
                    <code>{user.friendCode}</code>
                  </div>
                  <button type="button" className="dk-gold" onClick={copyFriendCode}>ID kopieren</button>
                </div>
              </div>
            )}
          </div>
        </section>

        {loading ? (
          <div className="dk-empty">Account wird geladen …</div>
        ) : user && (
          <>
            <nav className="ac-tabs" aria-label="Account Bereiche">
              {ACCOUNT_TABS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={accountTab === t.id ? "on" : ""}
                  aria-current={accountTab === t.id ? "page" : undefined}
                  onClick={() => openTab(t.id)}
                >
                  <i aria-hidden="true">{t.icon}</i>{t.label}
                </button>
              ))}
            </nav>

            {message && accountTab !== "profile" && (
              <div className="dk-note" role="status">{message}</div>
            )}

            {accountTab === "profile" && (
              <div className="ac-split">
                <section className="ac-panel">
                  <span className="ac-kicker">Profil</span>
                  <h2>Persönliche Daten</h2>
                  <p className="ac-lead">So sehen dich andere Sammler im Chat, auf dem Marktplatz und in deiner Vitrine.</p>

                  <label className="ac-field">
                    <span>Anzeigename</span>
                    <input
                      value={displayName}
                      maxLength={100}
                      placeholder="Dein Name"
                      onChange={(event) => setDisplayName(event.target.value)}
                    />
                  </label>

                  <label className="ac-field">
                    <span>E-Mail</span>
                    <input value={user.email} disabled />
                    <small>Die E-Mail-Adresse kann nicht geändert werden.</small>
                  </label>

                  {message && <div className="dk-note" role="status">{message}</div>}

                  <div className="ac-actions">
                    <button
                      className="dk-gold"
                      onClick={saveProfile}
                      disabled={saving || displayName === (user.displayName ?? "")}
                    >
                      {saving ? "Speichert …" : "Profil speichern"}
                    </button>
                  </div>
                </section>

                <aside className="ac-side">
                  <section className="ac-panel ac-mini">
                    <span className="ac-kicker">Sitzung</span>
                    <h3>Abmelden</h3>
                    <p>Meldet dich in diesem Browser ab. Die App bleibt angemeldet.</p>
                    <button className="dk-ghost" onClick={logout}>Abmelden</button>
                  </section>

                  <section className="ac-panel ac-mini ac-danger">
                    <span className="ac-kicker">Gefahrenzone</span>
                    <h3>Account löschen</h3>
                    <p>Löscht Sammlung, Wunschliste, Vitrine, Marktplatz-Daten und Chats endgültig.</p>
                    <button className="ac-dangerBtn" onClick={deleteAccount} disabled={deletingAccount}>
                      {deletingAccount ? "Account wird gelöscht …" : "Account dauerhaft löschen"}
                    </button>
                  </section>
                </aside>
              </div>
            )}

            {accountTab === "app" && (
              <section className="ac-panel ac-app">
                <div className="ac-phone" aria-hidden="true">
                  <div><span>✦</span><b>Cardyssey</b><i /><i /><i /></div>
                </div>
                <div>
                  <span className="ac-kicker">Android App</span>
                  <h2>Cardyssey für Android</h2>
                  <p className="ac-lead">Karten mit der Kamera scannen, Sammlung unterwegs ansehen und chatten. Hier gibt es immer die aktuellste Demo-Version.</p>
                  <p className="ac-release">
                    {androidRelease
                      ? <>Aktualisiert: <b>{formatAndroidReleaseDate(androidRelease.builtAt)}</b></>
                      : "Versionsinfo wird geladen …"}
                  </p>
                  <a className="dk-gold" href={ANDROID_APK_DOWNLOAD_URL}>Android App herunterladen</a>
                </div>
              </section>
            )}

            {accountTab === "security" && <div className="ac-panel ac-sub"><AccountSecurityPanel /></div>}
            {accountTab === "friends" && <div className="ac-panel ac-sub"><FriendsPanel embedded /></div>}
            {accountTab === "showcase" && <div className="ac-panel ac-sub"><ShowcaseSettingsPanel /></div>}
            {accountTab === "privacy" && <div className="ac-panel ac-sub"><PrivacySettingsPanel /></div>}
            {accountTab === "appearance" && <div className="ac-panel ac-sub"><AppearanceSettingsPanel /></div>}
          </>
        )}
      </div>
    </AppShell>
  );
}
