import Link from "next/link";
import { BrandMark } from "./BrandMark";
import type { User } from "@/lib/types";

const nav = [
  ["/collection", "Sammlung", "◫"],
  ["/scan", "Scannen", "⌗"],
  ["/sets", "Sets", "▦"],
  ["/shop", "Shop", "◇"],
  ["/marketplace", "Marktplatz", "◈"],
  ["/offers", "Angebote", "◎"],
  ["/friends", "Freunde", "♢"],
  ["/account", "Account", "○"],
] as const;

function initial(user?: User | null) {
  const source = user?.displayName || user?.email || "C";
  return source.trim().charAt(0).toUpperCase() || "C";
}

export function AppShell({ children, active, user }: { children: React.ReactNode; active: string; user?: User | null }) {
  const brand = process.env.NEXT_PUBLIC_BRAND_NAME || "Cardyssey";

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link className="brand" href="/collection">
          <BrandMark />
          <span>{brand}</span>
        </Link>
        <nav className="sideNav">
          {nav.map(([href, label, icon]) => (
            <Link key={href} href={href} className={active === href ? "navItem active" : "navItem"}>
              <span className="navIcon">{icon}</span>
              <span>{label}</span>
            </Link>
          ))}
        </nav>
        <Link href="/account" className="sidebarFoot">
          <div className="avatar">{initial(user)}</div>
          <div>
            <strong>{user?.displayName || "Account"}</strong>
            <span>{user?.email || "Anmelden & synchronisieren"}</span>
          </div>
        </Link>
      </aside>

      <div className="mainColumn">
        <header className="topbar">
          <div className="mobileBrand"><BrandMark /><b>{brand}</b></div>
          <div className="topbarRight">
            <button className="ghostButton">Deutsch</button>
            <Link href="/account" className="iconButton topbarAccount">○</Link>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>

      <nav className="bottomNav">
        {nav.slice(0, 4).map(([href, label, icon]) => (
          <Link key={href} href={href} className={active === href ? "bottomItem active" : "bottomItem"}>
            <span>{icon}</span><small>{label}</small>
          </Link>
        ))}
      </nav>
    </div>
  );
}
