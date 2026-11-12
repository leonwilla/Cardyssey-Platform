"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  AppShell,
} from "@/components/AppShell";

import type {
  User,
  UserRole,
} from "@/lib/types";

type Overview = {
  registeredUsers: number;
  activeUsers: number;
  collectionItems: number;
  collectionCards: number;
  wishlistItems: number;
  activeListings: number;
  pendingOffers: number;
};

type AdminUser = {
  id: string;
  email: string;
  displayName?: string | null;
  friendCode: string;
  role: UserRole;
  disabled: boolean;
  createdAt: string;
  collectionItems: number;
  collectionCards: number;
  wishlistItems: number;
  activeListings: number;
  pendingOffers: number;
};

type CollectionItem = {
  id: string;
  cardId: string;
  languageCode: string;
  name: string;
  setName?: string | null;
  localId?: string | null;
  variant: string;
  condition: string;
  quantity: number;
  valuedUnitEur?: number | null;
  positionValueEur?: number | null;
};

type DuplicateCard = {
  cardId: string;
  languageCode: string;
  name: string;
  setName?: string | null;
  localId?: string | null;
  variantKey: string;
  variant: string;
  quantity: number;
};

type WishlistItem = {
  id: string;
  cardId: string;
  languageCode: string;
  name: string;
  setName?: string | null;
  localId?: string | null;
  variantId?: string | null;
  createdAt: string;
};

type Listing = {
  id: string;
  collectionItemId: string;
  cardId: string;
  name: string;
  quantity: number;
  priceEur?: number | null;
  negotiable: boolean;
  status: string;
  createdAt: string;
};

type UserDetail = {
  user: AdminUser;
  collection: CollectionItem[];
  wishlist: WishlistItem[];
  listings: Listing[];
};

type SystemStatus = {
  database: string;
  service: string;
  version: string;
  justTcgConfigured: boolean;
  soldCompsConfigured: boolean;
  registeredUsers: number;
  collectionItems: number;
};

function formatDate(value: string) {
  try {
    return new Intl.DateTimeFormat(
      "de-DE",
      {
        dateStyle: "medium",
        timeStyle: "short",
      }
    ).format(new Date(value));
  } catch {
    return value;
  }
}

function euro(value?: number | null) {
  if (value == null) return "—";

  return new Intl.NumberFormat(
    "de-DE",
    {
      style: "currency",
      currency: "EUR",
    }
  ).format(value);
}

function roleLabel(role: UserRole) {
  if (role === "FOUNDER") return "◆ Founder";
  if (role === "ADMIN") return "◆ Admin";
  return "User";
}

function isRuntimeSmokeBot(
  entry: Pick<AdminUser, "email" | "displayName">
) {
  const email = entry.email.trim().toLowerCase();

  return (
    email.startsWith("runtime-smoke-") &&
    email.endsWith("@cardyssey.de")
  ) || entry.displayName === "Cardyssey Runtime Smoke";
}

function deleteErrorMessage(error?: string) {
  switch (error) {
    case "cannot_delete_self":
      return "Deinen eigenen Founder-Account kannst du nicht löschen.";
    case "cannot_delete_founder":
      return "Founder-Accounts sind vor dem Löschen geschützt.";
    case "cannot_delete_system_bot":
      return "Der Runtime-Smoke-Bot ist ein geschützter Systemaccount.";
    case "user_not_found":
      return "Der Account existiert nicht mehr.";
    case "founder_required":
      return "Nur der Founder darf Accounts endgültig löschen.";
    default:
      return "Account konnte nicht gelöscht werden.";
  }
}

export default function AdminPage() {
  const router = useRouter();

  const [user, setUser] =
    useState<User | null>(null);
  const [overview, setOverview] =
    useState<Overview | null>(null);
  const [users, setUsers] =
    useState<AdminUser[]>([]);
  const [detail, setDetail] =
    useState<UserDetail | null>(null);
  const [system, setSystem] =
    useState<SystemStatus | null>(null);
  const [search, setSearch] =
    useState("");
  const [loading, setLoading] =
    useState(true);
  const [detailLoading, setDetailLoading] =
    useState(false);
  const [deletingId, setDeletingId] =
    useState<string | null>(null);
  const [duplicates, setDuplicates] =
    useState<DuplicateCard[] | null>(null);
  const [duplicatesLoading, setDuplicatesLoading] =
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
        await fetch(
          "/api/auth/me",
          { cache: "no-store" }
        );

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
        me.canAdmin !== true &&
        me.role !== "ADMIN" &&
        me.role !== "FOUNDER"
      ) {
        router.replace("/account");
        return;
      }

      setUser(me);

      const [overviewResponse, usersResponse] =
        await Promise.all([
          fetch(
            "/api/admin/overview",
            { cache: "no-store" }
          ),
          fetch(
            "/api/admin/users",
            { cache: "no-store" }
          ),
        ]);

      if (
        !overviewResponse.ok ||
        !usersResponse.ok
      ) {
        throw new Error(
          "Control Center konnte nicht geladen werden."
        );
      }

      setOverview(
        await overviewResponse.json()
      );

      const loadedUsers =
        await usersResponse.json() as AdminUser[];

      setUsers(loadedUsers);

      if (loadedUsers.length > 0) {
        void loadUser(
          loadedUsers[0].id
        );
      } else {
        setDetail(null);
      }

      if (me.role === "FOUNDER") {
        const systemResponse =
          await fetch(
            "/api/admin/system",
            { cache: "no-store" }
          );

        if (systemResponse.ok) {
          setSystem(
            await systemResponse.json()
          );
        }
      }
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Control Center konnte nicht geladen werden."
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadUsers(
    query = search
  ) {
    setMessage(null);

    const params =
      new URLSearchParams();

    if (query.trim()) {
      params.set(
        "q",
        query.trim()
      );
    }

    try {
      const response =
        await fetch(
          `/api/admin/users${
            params.size
              ? `?${params.toString()}`
              : ""
          }`,
          { cache: "no-store" }
        );

      if (!response.ok) {
        throw new Error(
          "Nutzer konnten nicht geladen werden."
        );
      }

      setUsers(
        await response.json()
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Nutzer konnten nicht geladen werden."
      );
    }
  }

  async function loadUser(id: string) {
    setDetailLoading(true);
    setMessage(null);
    setDuplicates(null);

    try {
      const response =
        await fetch(
          `/api/admin/users/${
            encodeURIComponent(id)
          }`,
          { cache: "no-store" }
        );

      if (!response.ok) {
        throw new Error(
          "Nutzerdetails konnten nicht geladen werden."
        );
      }

      setDetail(
        await response.json()
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Nutzerdetails konnten nicht geladen werden."
      );
    } finally {
      setDetailLoading(false);
    }
  }

  async function deleteUserAccount(
    entry: AdminUser
  ) {
    if (user?.role !== "FOUNDER") {
      setMessage(
        "Nur der Founder darf Accounts endgültig löschen."
      );
      return;
    }

    if (
      entry.id === user.id ||
      entry.role === "FOUNDER" ||
      isRuntimeSmokeBot(entry)
    ) {
      setMessage(
        "Dieser Account ist vor dem Löschen geschützt."
      );
      return;
    }

    const confirmed =
      window.confirm(
        `Account ${entry.displayName || entry.email} wirklich ENDGÜLTIG löschen?\n\n` +
        "Sammlung, Wishlist, Listings, Angebote, Freundschaften und Sessions werden mit gelöscht. " +
        "Das kann nicht rückgängig gemacht werden."
      );

    if (!confirmed) return;

    setDeletingId(entry.id);
    setMessage(null);

    try {
      const response =
        await fetch(
          `/api/admin/users/${
            encodeURIComponent(entry.id)
          }`,
          {
            method: "DELETE",
          }
        );

      const payload =
        await response
          .json()
          .catch(() => ({})) as {
            error?: string;
          };

      if (!response.ok) {
        throw new Error(
          deleteErrorMessage(payload.error)
        );
      }

      setDetail(null);
      await initialize();
      setMessage(
        `Account ${entry.displayName || entry.email} wurde vollständig gelöscht.`
      );

    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Account konnte nicht gelöscht werden."
      );
    } finally {
      setDeletingId(null);
    }
  }

  async function copyDuplicates() {
    if (!duplicates) return;

    const rows = [
      ["Menge", "Name", "Set", "Nummer", "Sprache", "Variante", "Card-ID"],
      ...duplicates.map((item) => [
        String(item.quantity),
        item.name,
        item.setName || "",
        item.localId || "",
        item.languageCode.toUpperCase(),
        item.variant,
        item.cardId,
      ]),
    ];

    const text = rows
      .map((row) =>
        row
          .map((value) => String(value).replace(/\t|\r?\n/g, " "))
          .join("\t")
      )
      .join("\n");

    try {
      await navigator.clipboard.writeText(text);
      setMessage(
        duplicates.length === 1
          ? "1 doppelte Kartenposition wurde kopiert."
          : `${duplicates.length} doppelte Kartenpositionen wurden kopiert.`
      );
    } catch {
      setMessage("Die Liste konnte nicht in die Zwischenablage kopiert werden.");
    }
  }

  async function loadDuplicates(userId: string) {
    setDuplicatesLoading(true);
    setMessage(null);

    try {
      const response =
        await fetch(
          `/api/admin/users/${encodeURIComponent(userId)}/duplicates`,
          { cache: "no-store" }
        );

      if (!response.ok) {
        throw new Error(
          "Doppelte Karten konnten nicht ausgewertet werden."
        );
      }

      setDuplicates(
        await response.json() as DuplicateCard[]
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Doppelte Karten konnten nicht ausgewertet werden."
      );
    } finally {
      setDuplicatesLoading(false);
    }
  }

  function submitSearch(
    event: FormEvent
  ) {
    event.preventDefault();
    void loadUsers();
  }

  const selectedProtected =
    detail != null && (
      detail.user.id === user?.id ||
      detail.user.role === "FOUNDER" ||
      isRuntimeSmokeBot(detail.user)
    );

  return (
    <AppShell
      active="/admin"
      user={user}
    >
      <section className="pageIntro">
        <div>
          <span className="eyebrowText">
            Cardyssey Control Center
          </span>
          <h1>
            {user?.role === "FOUNDER"
              ? "Founder Dashboard"
              : "Admin Dashboard"}
          </h1>
          <p>
            Zentrale, serverseitig geschützte Übersicht über Nutzer,
            Sammlungen, Marketplace und Systemstatus. Founder können
            unerwünschte Accounts vollständig entfernen.
          </p>
        </div>

        <span
          className="chip"
          style={{
            color: "var(--gold)",
            borderColor: "rgba(255,209,102,.25)",
          }}
        >
          {user?.role === "FOUNDER"
            ? "◆ Founder Access"
            : "◆ Admin Access"}
        </span>
      </section>

      {loading ? (
        <div className="statusPanel">
          Control Center wird geladen …
        </div>
      ) : (
        <>
          {message && (
            <div className="statusPanel">
              {message}
            </div>
          )}

          {overview && (
            <section className="statsGrid founderOverview">
              <div className="statCard heroStat">
                <span>Registrierte Nutzer</span>
                <strong>
                  {overview.registeredUsers}
                </strong>
                <small>
                  {overview.activeUsers} aktiv
                </small>
              </div>
              <div className="statCard">
                <span>Karten</span>
                <strong>
                  {overview.collectionCards}
                </strong>
                <small>
                  {overview.collectionItems} Positionen
                </small>
              </div>
              <div className="statCard">
                <span>Marketplace</span>
                <strong>
                  {overview.activeListings}
                </strong>
                <small>aktive Listings</small>
              </div>
              <div className="statCard">
                <span>Angebote</span>
                <strong>
                  {overview.pendingOffers}
                </strong>
                <small>
                  {overview.wishlistItems} Wishlist-Einträge
                </small>
              </div>
            </section>
          )}

          {user?.role === "FOUNDER" && system && (
            <section className="sectionBlock">
              <div className="sectionTitle">
                <div>
                  <span className="eyebrowText">
                    Founder
                  </span>
                  <h2>Systemstatus</h2>
                </div>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "10px",
                  flexWrap: "wrap",
                  marginBottom: "14px",
                }}
              >
                {duplicates && (
                  <button
                    type="button"
                    className="ghostButton"
                    onClick={() => void copyDuplicates()}
                  >
                    Liste kopieren
                  </button>
                )}
                <button
                  type="button"
                  className="primaryButton"
                  disabled={duplicatesLoading}
                  onClick={async () => {
                    if (!user?.id) return;
                    await loadUser(user.id);
                    await loadDuplicates(user.id);
                  }}
                >
                  {duplicatesLoading
                    ? "Duplikate werden ausgewertet …"
                    : "Meine Duplikate auswerten"}
                </button>
              </div>

              <div className="statsGrid founderSystemGrid">
                <div className="statCard">
                  <span>Backend</span>
                  <strong style={{ color: "var(--lime)" }}>
                    ● Online
                  </strong>
                  <small>
                    {system.service} · {system.version}
                  </small>
                </div>
                <div className="statCard">
                  <span>PostgreSQL</span>
                  <strong style={{ color: system.database === "connected" ? "var(--lime)" : "var(--pink)" }}>
                    ● {system.database === "connected" ? "Online" : "Problem"}
                  </strong>
                  <small>
                    {system.registeredUsers} Nutzer
                  </small>
                </div>
                <div className="statCard">
                  <span>JustTCG</span>
                  <strong style={{ color: system.justTcgConfigured ? "var(--lime)" : "var(--gold)" }}>
                    ● {system.justTcgConfigured ? "Konfiguriert" : "Nicht konfiguriert"}
                  </strong>
                  <small>Secret wird niemals angezeigt</small>
                </div>
                <div className="statCard">
                  <span>SoldComps</span>
                  <strong style={{ color: system.soldCompsConfigured ? "var(--lime)" : "var(--gold)" }}>
                    ● {system.soldCompsConfigured ? "Konfiguriert" : "Nicht konfiguriert"}
                  </strong>
                  <small>Secret wird niemals angezeigt</small>
                </div>
              </div>
            </section>
          )}

          <section className="sectionBlock">
            <div className="sectionTitle">
              <div>
                <span className="eyebrowText">
                  Verwaltung
                </span>
                <h2>Nutzer</h2>
              </div>
              <span className="chip mutedChip">
                {user?.role === "FOUNDER"
                  ? "Founder-Verwaltung"
                  : "Read-only"}
              </span>
            </div>

            <form
              onSubmit={submitSearch}
              className="filterRow"
            >
              <input
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
                placeholder="Name, E-Mail oder Cardyssey-ID"
                style={{
                  minHeight: "42px",
                  width: "min(520px, 100%)",
                  borderRadius: "12px",
                  border: "1px solid var(--border)",
                  background: "#09111e",
                  color: "var(--text)",
                  padding: "0 14px",
                  font: "inherit",
                }}
              />
              <button className="ghostButton">
                Suchen
              </button>
              {search && (
                <button
                  type="button"
                  className="ghostButton"
                  onClick={() => {
                    setSearch("");
                    void loadUsers("");
                  }}
                >
                  Zurücksetzen
                </button>
              )}
            </form>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(280px, .85fr) minmax(0, 1.7fr)",
                gap: "16px",
                alignItems: "start",
              }}
            >
              <div
                style={{
                  display: "grid",
                  gap: "10px",
                }}
              >
                {users.map((entry) => (
                  <button
                    key={entry.id}
                    type="button"
                    className="statusPanel"
                    onClick={() =>
                      void loadUser(entry.id)
                    }
                    style={{
                      cursor: "pointer",
                      textAlign: "left",
                      color: "var(--text)",
                      font: "inherit",
                      width: "100%",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "12px",
                        alignItems: "start",
                      }}
                    >
                      <div>
                        <strong>
                          {entry.displayName || "Cardyssey Collector"}
                        </strong>
                        <div className="muted">
                          {entry.email}
                        </div>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          gap: "6px",
                          flexWrap: "wrap",
                          justifyContent: "flex-end",
                        }}
                      >
                        {isRuntimeSmokeBot(entry) && (
                          <span
                            className="chip"
                            style={{ color: "var(--cyan)" }}
                          >
                            BOT
                          </span>
                        )}
                        <span
                          className="chip"
                          style={{
                            color: entry.role === "FOUNDER" ? "var(--gold)" : undefined,
                          }}
                        >
                          {roleLabel(entry.role)}
                        </span>
                      </div>
                    </div>
                    <div className="chips">
                      <span className="chip mutedChip">
                        {entry.collectionCards} Karten
                      </span>
                      <span className="chip mutedChip">
                        {entry.activeListings} Listings
                      </span>
                      {entry.disabled && (
                        <span className="chip">
                          Deaktiviert
                        </span>
                      )}
                    </div>
                  </button>
                ))}

                {users.length === 0 && (
                  <div className="statusPanel">
                    Keine Nutzer gefunden.
                  </div>
                )}
              </div>

              <div className="statusPanel">
                {detailLoading ? (
                  "Nutzerdetails werden geladen …"
                ) : detail ? (
                  <div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "18px",
                        alignItems: "start",
                        flexWrap: "wrap",
                      }}
                    >
                      <div>
                        <div
                          style={{
                            display: "flex",
                            gap: "6px",
                            alignItems: "center",
                            flexWrap: "wrap",
                          }}
                        >
                          <span className="eyebrowText">
                            {roleLabel(detail.user.role)}
                          </span>
                          {isRuntimeSmokeBot(detail.user) && (
                            <span
                              className="chip"
                              style={{ color: "var(--cyan)" }}
                            >
                              BOT
                            </span>
                          )}
                        </div>
                        <h2 style={{ marginBottom: "6px" }}>
                          {detail.user.displayName || "Cardyssey Collector"}
                        </h2>
                        <div>{detail.user.email}</div>
                        <div className="muted">
                          {detail.user.friendCode}
                        </div>
                      </div>

                      <div
                        style={{
                          display: "grid",
                          justifyItems: "end",
                          gap: "10px",
                        }}
                      >
                        <div className="muted">
                          Beigetreten: {formatDate(detail.user.createdAt)}
                        </div>

                        {user?.role === "FOUNDER" && !selectedProtected && (
                          <button
                            type="button"
                            className="ghostButton"
                            disabled={deletingId === detail.user.id}
                            onClick={() =>
                              void deleteUserAccount(detail.user)
                            }
                            style={{
                              color: "var(--pink)",
                              borderColor: "rgba(255,90,130,.45)",
                            }}
                          >
                            {deletingId === detail.user.id
                              ? "Wird gelöscht …"
                              : "Account endgültig löschen"}
                          </button>
                        )}

                        {user?.role === "FOUNDER" && selectedProtected && (
                          <span className="chip mutedChip">
                            Geschützter Account
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="chips">
                      <span className="chip">
                        {detail.user.collectionCards} Karten
                      </span>
                      <span className="chip">
                        {detail.user.wishlistItems} Wishlist
                      </span>
                      <span className="chip">
                        {detail.user.activeListings} Listings
                      </span>
                      <span className="chip">
                        {detail.user.pendingOffers} offene Angebote
                      </span>
                    </div>

                    <div className="sectionBlock">
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: "12px",
                          flexWrap: "wrap",
                        }}
                      >
                        <div>
                          <h3 style={{ marginBottom: "4px" }}>
                            Doppelte Karten
                          </h3>
                          <div className="muted">
                            Gleiche Karte, Sprache und physische Variante werden zusammengezählt.
                          </div>
                        </div>
                        <div
                          style={{
                            display: "flex",
                            gap: "8px",
                            flexWrap: "wrap",
                          }}
                        >
                          {duplicates && (
                            <button
                              type="button"
                              className="ghostButton"
                              onClick={() => void copyDuplicates()}
                            >
                              Liste kopieren
                            </button>
                          )}
                          <button
                            type="button"
                            className="ghostButton"
                            disabled={duplicatesLoading}
                            onClick={() =>
                              void loadDuplicates(detail.user.id)
                            }
                          >
                            {duplicatesLoading
                              ? "Wird ausgewertet …"
                              : "Duplikate auswerten"}
                          </button>
                        </div>
                      </div>

                      {duplicates && (
                        <div
                          style={{
                            display: "grid",
                            gap: "8px",
                            marginTop: "14px",
                          }}
                        >
                          <div className="muted">
                            {duplicates.length} doppelte Kartenpositionen gefunden
                          </div>
                          {duplicates.map((item) => (
                            <div
                              key={`${item.cardId}:${item.languageCode}:${item.variantKey}`}
                              style={{
                                display: "grid",
                                gridTemplateColumns: "1fr auto",
                                gap: "12px",
                                padding: "9px 0",
                                borderBottom: "1px solid rgba(38,58,85,.45)",
                              }}
                            >
                              <div>
                                <strong>{item.name}</strong>
                                <div className="muted">
                                  {item.setName || "—"} · {item.localId || item.cardId} · {item.languageCode.toUpperCase()} · {item.variant}
                                </div>
                              </div>
                              <strong>× {item.quantity}</strong>
                            </div>
                          ))}
                          {duplicates.length === 0 && (
                            <span className="muted">
                              Keine doppelten Karten gefunden.
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="sectionBlock">
                      <h3>Sammlung</h3>
                      <div style={{ display: "grid", gap: "8px" }}>
                        {detail.collection.slice(0, 50).map((item) => (
                          <div
                            key={item.id}
                            style={{
                              display: "grid",
                              gridTemplateColumns: "1fr auto auto",
                              gap: "12px",
                              padding: "10px 0",
                              borderBottom: "1px solid rgba(38,58,85,.45)",
                            }}
                          >
                            <div>
                              <strong>{item.name}</strong>
                              <div className="muted">
                                {item.setName || "—"} · {item.localId || item.cardId} · {item.languageCode.toUpperCase()}
                              </div>
                            </div>
                            <span>
                              × {item.quantity}
                            </span>
                            <strong className="price">
                              {euro(item.positionValueEur)}
                            </strong>
                          </div>
                        ))}
                        {detail.collection.length === 0 && (
                          <span className="muted">
                            Keine Sammlungseinträge.
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="sectionBlock">
                      <h3>Wishlist</h3>
                      <div style={{ display: "grid", gap: "6px" }}>
                        {detail.wishlist.slice(0, 30).map((item) => (
                          <div key={item.id}>
                            <strong>{item.name}</strong>
                            <span className="muted">
                              {" · "}{item.setName || item.cardId}
                            </span>
                          </div>
                        ))}
                        {detail.wishlist.length === 0 && (
                          <span className="muted">
                            Keine Wishlist-Einträge.
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="sectionBlock">
                      <h3>Listings</h3>
                      <div style={{ display: "grid", gap: "6px" }}>
                        {detail.listings.slice(0, 30).map((listing) => (
                          <div
                            key={listing.id}
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              gap: "12px",
                            }}
                          >
                            <span>
                              {listing.name} × {listing.quantity}
                            </span>
                            <strong>
                              {euro(listing.priceEur)} · {listing.status}
                            </strong>
                          </div>
                        ))}
                        {detail.listings.length === 0 && (
                          <span className="muted">
                            Keine Listings.
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  "Nutzer auswählen."
                )}
              </div>
            </div>
          </section>
        </>
      )}
    </AppShell>
  );
}
