"use client";

import "../deck.css";
import "./market.css";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  AppShell,
} from "@/components/AppShell";
import OffersPage from "@/app/offers/page";

import type {
  User,
} from "@/lib/types";

type Listing = {
  id: string;
  sellerFriendCode: string;
  sellerDisplayName?: string | null;
  cardId: string;
  languageCode: string;
  name: string;
  setName?: string | null;
  localId?: string | null;
  imageBase?: string | null;
  variant: string;
  condition: string;
  quantity: number;
  priceEur?: number | null;
  negotiable: boolean;
};

function imageUrl(
  base?: string | null
) {
  return base
    ? `${base.replace(/\/$/, "")}/high.webp`
    : null;
}

function money(
  value?: number | null
) {
  return value == null
    ? "Preis auf Anfrage"
    : new Intl.NumberFormat(
        "de-DE",
        {
          style: "currency",
          currency: "EUR",
        }
      ).format(value);
}

export default function MarketplacePage() {
  const router = useRouter();

  const [user, setUser] =
    useState<User | null>(null);

  const [listings, setListings] =
    useState<Listing[]>([]);

  const [marketTab,setMarketTab]=useState<"browse"|"offers">("offers");

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("tab") === "browse") setMarketTab("browse");
  }, []);

  const [query, setQuery] =
    useState("");

  const [sort, setSort] =
    useState<"new" | "priceAsc" | "priceDesc" | "name">("new");

  const [counts, setCounts] =
    useState({ incoming: 0, outgoing: 0, pending: 0 });

  const [loading, setLoading] =
    useState(true);

  useEffect(() => {
    async function load() {
      const [me, market] =
        await Promise.all([
          fetch("/api/auth/me", {
            cache: "no-store",
          }),
          fetch("/api/marketplace", {
            cache: "no-store",
          }),
        ]);

      if (me.status === 401) {
        router.replace("/login");
        return;
      }

      if (me.ok) {
        setUser(await me.json());
      }

      if (market.ok) {
        setListings(
          await market.json()
        );
      }

      setLoading(false);
    }

    load();
  }, [router]);

  const filtered =
    useMemo(() => {
      const q =
        query.trim().toLowerCase();

      if (!q) {
        return listings;
      }

      return listings.filter(
        (listing) =>
          [
            listing.name,
            listing.setName,
            listing.variant,
            listing.condition,
            listing.sellerDisplayName,
          ]
            .filter(Boolean)
            .some(
              (value) =>
                String(value)
                  .toLowerCase()
                  .includes(q)
            )
      );
    }, [
      listings,
      query,
    ]);

  const sorted = useMemo(() => {
    const list = [...filtered];
    const price = (l: Listing) => l.priceEur ?? Number.POSITIVE_INFINITY;
    if (sort === "priceAsc") list.sort((a, b) => price(a) - price(b));
    if (sort === "priceDesc") list.sort((a, b) => (b.priceEur ?? -1) - (a.priceEur ?? -1));
    if (sort === "name") list.sort((a, b) => a.name.localeCompare(b.name, "de"));
    return list;
  }, [filtered, sort]);

  const sellers = useMemo(
    () => new Set(listings.map((l) => l.sellerFriendCode)).size,
    [listings]
  );

  return (
    <AppShell
      active="/marketplace"
      user={user}
    >
      <div className="dk mk">
        <section className="dk-deck">
          <div className="dk-deckGrid">
            <div>
              <span className="dk-eyebrow">Cardyssey</span>
              <h1 className="dk-title">Marktplatz</h1>
              <p className="dk-sub">Karten von anderen Sammlern, deine Kaufangebote und der offizielle Cardyssey-Store an einem Tisch.</p>
              <div className="dk-stats">
                <div className="dk-stat"><b>{loading ? "…" : listings.length}</b><span>Karten im Angebot</span></div>
                <div className="dk-stat"><b>{loading ? "…" : sellers}</b><span>Verkäufer</span></div>
                <div className="dk-stat"><b>{counts.pending}</b><span>offene Anfragen</span></div>
                <div className="dk-stat"><b>{counts.outgoing}</b><span>gesendet</span></div>
              </div>
            </div>
            <div className="mk-deckSide">
              <a className="mk-store" href="https://shop.cardyssey.de/">
                <span className="mk-storeMark" aria-hidden="true">✦</span>
                <span>
                  <small>Offizieller Cardyssey Store</small>
                  <strong>Du suchst eine bestimmte Karte?</strong>
                  <em>Shopsortiment mit demselben Konto ansehen ↗</em>
                </span>
              </a>
              <button type="button" className="dk-gold" onClick={() => router.push("/selling")}>Eigene Karten verkaufen</button>
            </div>
          </div>
        </section>

        <div className="mk-tabs">
          <div className="dk-seg" role="tablist" aria-label="Marktplatz-Bereiche">
            <button role="tab" aria-selected={marketTab === "offers"} className={marketTab === "offers" ? "on" : ""} onClick={() => setMarketTab("offers")}>Meine Angebote<b>{counts.incoming + counts.outgoing}</b></button>
            <button role="tab" aria-selected={marketTab === "browse"} className={marketTab === "browse" ? "on" : ""} onClick={() => setMarketTab("browse")}>Karten entdecken<b>{listings.length}</b></button>
          </div>
        </div>

        <div hidden={marketTab !== "offers"}>
          <OffersPage embedded onDiscover={() => setMarketTab("browse")} onCounts={setCounts} />
        </div>

        {marketTab === "browse" && (
          <>
            <div className="dk-tools">
              <div className="dk-toolRow">
                <label className="dk-search">
                  <span aria-hidden="true">⌕</span>
                  <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Karte, Set, Variante oder Verkäufer …" aria-label="Marktplatz durchsuchen" />
                </label>
                <label className="dk-pill">Sortieren
                  <select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}>
                    <option value="new">Neueste</option>
                    <option value="priceAsc">Preis aufsteigend</option>
                    <option value="priceDesc">Preis absteigend</option>
                    <option value="name">Name A–Z</option>
                  </select>
                </label>
                <span className="dk-count">{sorted.length} von {listings.length} Karten</span>
              </div>
            </div>

            {loading ? (
              <div className="dk-empty">Marktplatz wird geladen …</div>
            ) : sorted.length === 0 ? (
              <div className="dk-empty">{listings.length === 0 ? "Gerade bietet niemand Karten an. Sei der Erste und stell eigene Karten ein." : "Keine Karte passt zu deiner Suche."}</div>
            ) : (
              <div className="dk-binder mk-binder">
                {sorted.map((listing) => {
                  const image = imageUrl(listing.imageBase);
                  return (
                    <button
                      type="button"
                      className="dk-pocket mk-listing"
                      key={listing.id}
                      onClick={() => router.push(`/friends/${encodeURIComponent(listing.sellerFriendCode)}`)}
                      title={`Profil von ${listing.sellerDisplayName ?? "Verkäufer"} ansehen`}
                    >
                      <div className="dk-art">
                        {image ? <img src={image} alt={listing.name} loading="lazy" /> : null}
                        <span className="dk-badge gold mk-price">{money(listing.priceEur)}</span>
                        {listing.quantity > 1 && <span className="dk-badge mk-qty">{listing.quantity}×</span>}
                        <span className="dk-plus">Zum Verkäufer</span>
                      </div>
                      <div>
                        <div className="dk-name" title={listing.name}>{listing.name}</div>
                        <div className="dk-meta">#{listing.localId ?? "—"} · {listing.setName ?? "Trading Card"}</div>
                      </div>
                      <div className="mk-chips">
                        <span>{listing.languageCode.toUpperCase()}</span>
                        <span>{listing.variant}</span>
                        <span>{listing.condition}</span>
                        {listing.negotiable && <span className="vb">VB</span>}
                      </div>
                      <div className="mk-seller"><i>{(listing.sellerDisplayName ?? "V").charAt(0).toUpperCase()}</i>{listing.sellerDisplayName ?? "Verkäufer"}</div>
                    </button>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
