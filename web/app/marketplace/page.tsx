"use client";

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

  const [query, setQuery] =
    useState("");

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

  return (
    <AppShell
      active="/marketplace"
      user={user}
    >
      <div className="pageHeader marketplaceHeader">
        <div>
          <span className="eyebrowText">
            Cardyssey
          </span>

          <h1>Marktplatz</h1>

          <p className="muted">
            Karten, die andere Sammler
            aktuell anbieten.
          </p>
        </div>

        <button
          className="primaryButton"
          onClick={
            () =>
              router.push("/selling")
          }
        >
          Eigene Karten verkaufen
        </button>
      </div>

      <div className="marketSearch">
        <input
          type="search"
          value={query}
          onChange={
            (event) =>
              setQuery(
                event.target.value
              )
          }
          placeholder="Karte, Set oder Variante suchen …"
        />
      </div>

      {loading ? (
        <div className="statusPanel">
          Marktplatz wird geladen …
        </div>
      ) : filtered.length === 0 ? (
        <div className="statusPanel">
          Aktuell keine passenden
          Verkaufsangebote.
        </div>
      ) : (
        <div className="marketGrid">
          {filtered.map(
            (listing) => {

              const image =
                imageUrl(
                  listing.imageBase
                );

              return (
                <article
                  className="marketCard"
                  key={listing.id}
                >
                  <div className="marketImage">
                    {image ? (
                      <img
                        src={image}
                        alt={listing.name}
                      />
                    ) : (
                      <div className="cardImagePlaceholder" />
                    )}
                  </div>

                  <div className="marketBody">
                    <span className="eyebrowText">
                      {listing.setName ??
                        "Trading Card"}
                    </span>

                    <h3>
                      {listing.name}
                    </h3>

                    <p className="muted">
                      #{listing.localId ?? "—"}
                    </p>

                    <div className="chips">
                      <span className="chip">
                        {listing.languageCode.toUpperCase()}
                      </span>

                      <span className="chip">
                        {listing.variant}
                      </span>

                      <span className="chip">
                        {listing.condition}
                      </span>

                      <span className="chip">
                        {listing.quantity}×
                      </span>
                    </div>

                    <div className="marketPrice">
                      {money(
                        listing.priceEur
                      )}

                      {listing.negotiable && (
                        <small>
                          verhandelbar
                        </small>
                      )}
                    </div>

                    <button
                      className="ghostButton"
                      onClick={
                        () =>
                          router.push(
                            `/friends/${
                              encodeURIComponent(
                                listing.sellerFriendCode
                              )
                            }`
                          )
                      }
                    >
                      {listing.sellerDisplayName ??
                        "Verkäufer"}
                      {" · Profil"}
                    </button>
                  </div>
                </article>
              );
            }
          )}
        </div>
      )}
    </AppShell>
  );
}
