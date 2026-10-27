"use client";

import Link from "next/link";
import {
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { BrandMark } from "./BrandMark";
import type { User } from "@/lib/types";

type NavIconName =
  | "collection"
  | "scan"
  | "sets"
  | "shop"
  | "marketplace"
  | "offers"
  | "friends"
  | "account"
  | "admin";

const nav: readonly [
  string,
  string,
  NavIconName,
][] = [
  ["/collection", "Sammlung", "collection"],
  ["/scan", "Scannen", "scan"],
  ["/sets", "Sets", "sets"],
  ["/shop", "Shop", "shop"],
  ["/marketplace", "Marktplatz", "marketplace"],
  ["/offers", "Angebote", "offers"],
  ["/friends", "Community", "friends"],
  ["/chat", "Nachrichten", "friends"],
  ["/account", "Account", "account"],
];

const mobileNav: readonly [
  string,
  string,
  NavIconName,
][] = [
  ["/collection", "Sammlung", "collection"],
  ["/scan", "Scannen", "scan"],
  ["/sets", "Sets", "sets"],
  ["/friends", "Community", "friends"],
  ["/account", "Account", "account"],
];

let cachedShellUser:
  | User
  | null
  | undefined;

function initial(user?: User | null) {
  const source =
    user?.displayName ||
    user?.email ||
    "C";

  return (
    source.trim().charAt(0).toUpperCase() ||
    "C"
  );
}

function NavGlyph({
  name,
}: {
  name: NavIconName;
}) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      {name === "collection" && (
        <>
          <rect
            x="5"
            y="4"
            width="12"
            height="16"
            rx="2"
            {...common}
          />
          <path
            d="M9 4v16M17 7h2v11a2 2 0 0 1-2 2"
            {...common}
          />
        </>
      )}

      {name === "scan" && (
        <>
          <path
            d="M8 4H5a1 1 0 0 0-1 1v3M16 4h3a1 1 0 0 1 1 1v3M8 20H5a1 1 0 0 1-1-1v-3M16 20h3a1 1 0 0 0 1-1v-3"
            {...common}
          />
          <path
            d="M7 12h10M12 7v10"
            {...common}
          />
        </>
      )}

      {name === "sets" && (
        <>
          <rect x="4" y="4" width="6" height="6" rx="1.3" {...common} />
          <rect x="14" y="4" width="6" height="6" rx="1.3" {...common} />
          <rect x="4" y="14" width="6" height="6" rx="1.3" {...common} />
          <rect x="14" y="14" width="6" height="6" rx="1.3" {...common} />
        </>
      )}

      {name === "shop" && (
        <>
          <path
            d="M5 8h14l-1 12H6L5 8Z"
            {...common}
          />
          <path
            d="M9 9V7a3 3 0 0 1 6 0v2"
            {...common}
          />
        </>
      )}

      {name === "marketplace" && (
        <>
          <path
            d="M4 9h16l-2-5H6L4 9Z"
            {...common}
          />
          <path
            d="M5 9v10h14V9M9 19v-6h6v6"
            {...common}
          />
          <path
            d="M4 9c0 2 3 2 4 0 1 2 3 2 4 0 1 2 3 2 4 0 1 2 4 2 4 0"
            {...common}
          />
        </>
      )}

      {name === "offers" && (
        <>
          <path
            d="M4 7V4h3l11 11-5 5L4 11V7Z"
            {...common}
          />
          <circle
            cx="7.5"
            cy="7.5"
            r="1"
            {...common}
          />
        </>
      )}

      {name === "friends" && (
        <>
          <circle
            cx="9"
            cy="8"
            r="3"
            {...common}
          />
          <path
            d="M3.5 19c.5-4 2.5-6 5.5-6s5 2 5.5 6"
            {...common}
          />
          <path
            d="M15 6.5a2.5 2.5 0 0 1 0 5M16 14c2.5.5 4 2 4.5 5"
            {...common}
          />
        </>
      )}

      {name === "account" && (
        <>
          <circle
            cx="12"
            cy="8"
            r="3.5"
            {...common}
          />
          <path
            d="M5 20c.6-4.5 3-6.5 7-6.5s6.4 2 7 6.5"
            {...common}
          />
        </>
      )}

      {name === "admin" && (
        <>
          <path
            d="M12 3 19 6v5c0 4.5-2.8 7.7-7 10-4.2-2.3-7-5.5-7-10V6l7-3Z"
            {...common}
          />
          <path
            d="m9 12 2 2 4-4"
            {...common}
          />
        </>
      )}
    </svg>
  );
}

export function AppShell({
  children,
  active,
  user,
}: {
  children: ReactNode;
  active: string;
  user?: User | null;
}) {
  const brand =
    process.env.NEXT_PUBLIC_BRAND_NAME ||
    "Cardyssey";

  const [
    shellUser,
    setShellUser,
  ] = useState<
    User | null | undefined
  >(
    user !== undefined
      ? user
      : cachedShellUser
  );

  useEffect(() => {
    if (user !== undefined) {
      cachedShellUser = user;
      setShellUser(user);
      return;
    }

    if (cachedShellUser !== undefined) {
      setShellUser(cachedShellUser);
    }

    let cancelled = false;

    fetch("/api/auth/me", {
      cache: "no-store",
    })
      .then(async (response) => {
        if (response.status === 401) {
          return null;
        }

        if (!response.ok) {
          throw new Error(
            "Accountstatus nicht verfügbar."
          );
        }

        return response.json() as Promise<User>;
      })
      .then((loadedUser) => {
        if (cancelled) return;

        cachedShellUser = loadedUser;
        setShellUser(loadedUser);
      })
      .catch(() => {
        // Bei einem temporären Fehler niemals
        // einen bekannten Login-Zustand löschen.
      });

    return () => {
      cancelled = true;
    };
  }, [user]);

  const accountLoading =
    shellUser === undefined;

  const canAdmin =
    shellUser?.canAdmin === true ||
    shellUser?.role === "ADMIN" ||
    shellUser?.role === "FOUNDER";

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link
          className="brand"
          href="/collection"
        >
          <BrandMark />
          <span>{brand}</span>
        </Link>

        <nav className="sideNav">
          {nav.map(
            ([href, label, icon]) => (
              <Link
                key={href}
                href={href}
                className={
                  active === href
                    ? "navItem active"
                    : "navItem"
                }
              >
                <span className="navIcon">
                  <NavGlyph name={icon} />
                </span>

                <span>{label}</span>
              </Link>
            )
          )}

          {canAdmin && (
            <>
              <Link
                href="/admin"
                className={
                  active === "/admin"
                    ? "navItem active adminNavItem"
                    : "navItem adminNavItem"
                }
              >
                <span className="navIcon">
                  <NavGlyph name="admin" />
                </span>

                <span>
                  Control Center
                </span>
              </Link>

              <Link href="/admin/shop-catalog" className={active === "/admin/shop-catalog" ? "navItem active adminNavItem" : "navItem adminNavItem"}>
                <span className="navIcon"><NavGlyph name="shop" /></span>
                <span>Kartenkatalog → Shop</span>
              </Link>

              <Link
                href="/admin/shop-listings"
                className={active === "/admin/shop-listings" ? "navItem active adminNavItem" : "navItem adminNavItem"}
              >
                <span className="navIcon"><NavGlyph name="shop" /></span>
                <span>Einzelkarten listen</span>
              </Link>

              <Link
                href="/admin/prices"
                className={
                  active === "/admin/prices"
                    ? "navItem active adminNavItem"
                    : "navItem adminNavItem"
                }
              >
                <span className="navIcon">
                  <NavGlyph name="marketplace" />
                </span>
                <span>Preis-Monitoring</span>
              </Link>

              <Link
                href="/admin/chat"
                className={
                  active === "/admin/chat"
                    ? "navItem active adminNavItem"
                    : "navItem adminNavItem"
                }
              >
                <span className="navIcon">
                  <NavGlyph name="friends" />
                </span>

                <span>
                  Chat-Moderation
                </span>
              </Link>
            </>
          )}
        </nav>

        <Link
          href="/account"
          className="sidebarFoot"
        >
          <div className="avatar sidebarAvatar">
            {accountLoading
              ? "·"
              : initial(shellUser)}
          </div>

          <div className="sidebarFootText">
            <div className="sidebarFootTitle">
              <strong>
                {accountLoading
                  ? "Account"
                  : shellUser?.displayName ||
                    "Account"}
              </strong>

              {shellUser?.role ===
                "FOUNDER" && (
                <span className="sidebarFootBadge founder">
                  ◆ Founder
                </span>
              )}

              {shellUser?.role ===
                "ADMIN" && (
                <span className="sidebarFootBadge admin">
                  ◆ Admin
                </span>
              )}
            </div>

            <span className="sidebarFootSub">
              {accountLoading
                ? "Account wird geladen …"
                : shellUser?.email ||
                  "Anmelden & synchronisieren"}
            </span>
          </div>

          <span className="sidebarFootArrow">
            ›
          </span>
        </Link>
      </aside>

      <div className="mainColumn">
        <header className="topbar">
          <div className="mobileBrand">
            <BrandMark />
            <b>{brand}</b>
          </div>

          <div className="topbarRight">
            {canAdmin && (
              <Link
                href="/admin"
                className="ghostButton"
                style={{
                  display: "grid",
                  placeItems: "center",
                }}
              >
                ◆ Control Center
              </Link>
            )}

            <button className="ghostButton">
              Deutsch
            </button>

            <Link
              href="/account"
              className="iconButton topbarAccount"
              aria-label="Account"
            >
              <NavGlyph name="account" />
            </Link>
          </div>
        </header>

        <main className="content">
          {children}
        </main>

        <footer className="appLegalFooter">
          <Link href="/impressum">Impressum</Link>
          <Link href="/datenschutz">Datenschutz</Link>
          <span>© 2026 Cardyssey</span>
        </footer>
      </div>

      <nav className="bottomNav">
        {mobileNav.map(
            ([href, label, icon]) => (
              <Link
                key={href}
                href={href}
                className={
                  active === href
                    ? "bottomItem active"
                    : "bottomItem"
                }
              >
                <NavGlyph name={icon} />
                <small>{label}</small>
              </Link>
            )
          )}
      </nav>
    </div>
  );
}
