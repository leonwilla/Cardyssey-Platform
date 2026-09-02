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

import type {
  User,
} from "@/lib/types";

type WishlistItem = {
  id: string;
  cardId: string;
  languageCode: string;
  name: string;
  setId?: string | null;
  setName?: string | null;
  localId?: string | null;
  imageBase?: string | null;
  variantId?: string | null;
  variantType?: string | null;
  variantSubtype?: string | null;
  foil?: string | null;
  size?: string | null;
  stamps: string[];
};

function cardImage(
  base?: string | null
) {
  return base
    ? `${base.replace(/\/$/, "")}/high.webp`
    : null;
}

export default function WishlistPage() {
  const router = useRouter();

  const [user, setUser] =
    useState<User | null>(null);

  const [items, setItems] =
    useState<WishlistItem[]>([]);

  const [loading, setLoading] =
    useState(true);

  async function load() {
    const [me, wishlist] =
      await Promise.all([
        fetch("/api/auth/me", {
          cache: "no-store",
        }),
        fetch("/api/wishlist", {
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

    if (wishlist.ok) {
      setItems(
        await wishlist.json()
      );
    }

    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function remove(id: string) {
    const response =
      await fetch(
        `/api/wishlist/${
          encodeURIComponent(id)
        }`,
        {
          method: "DELETE",
        }
      );

    if (response.ok) {
      setItems(
        items.filter(
          (item) => item.id !== id
        )
      );
    }
  }

  return (
    <AppShell
      active="/wishlist"
      user={user}
    >
      <div className="pageHeader">
        <div>
          <span className="eyebrowText">
            Gesucht
          </span>

          <h1>Wishlist</h1>

          <p className="muted">
            Karten, die du suchst.
            Später können andere Sammler
            dir dafür Angebote machen.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="statusPanel">
          Wishlist wird geladen …
        </div>
      ) : items.length === 0 ? (
        <div className="statusPanel">
          Deine Wishlist ist noch leer.
          Füge Karten über die Kartensuche hinzu.
        </div>
      ) : (
        <div className="wishlistGrid">
          {items.map((item) => {
            const image =
              cardImage(item.imageBase);

            const variant = [
              item.variantType,
              item.variantSubtype,
              item.foil,
              ...item.stamps,
            ]
              .filter(Boolean)
              .join(" · ");

            return (
              <article
                className="wishlistCard"
                key={item.id}
              >
                <div className="wishlistImage">
                  {image ? (
                    <img
                      src={image}
                      alt={item.name}
                    />
                  ) : (
                    <div className="cardImagePlaceholder" />
                  )}
                </div>

                <div>
                  <span className="eyebrowText">
                    Gesucht
                  </span>

                  <h3>{item.name}</h3>

                  <p className="muted">
                    {item.setName ??
                      "Unbekanntes Set"}
                    {" · #"}
                    {item.localId ?? "—"}
                  </p>

                  <div className="chips">
                    <span className="chip">
                      {item.languageCode.toUpperCase()}
                    </span>

                    {variant && (
                      <span className="chip mutedChip">
                        {variant}
                      </span>
                    )}
                  </div>
                </div>

                <button
                  className="ghostButton"
                  onClick={
                    () => remove(item.id)
                  }
                >
                  Entfernen
                </button>
              </article>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
