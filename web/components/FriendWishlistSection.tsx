"use client";

import Image from "next/image";

import {
  useEffect,
  useState,
} from "react";

type WishlistItem = {
  id: string;
  cardId: string;
  languageCode: string;
  name: string;
  setName?: string | null;
  localId?: string | null;
  imageBase?: string | null;
  variantType?: string | null;
  variantSubtype?: string | null;
  foil?: string | null;
  stamps: string[];
};

type Props = {
  friendCode: string;
  visible: boolean;
};

export function FriendWishlistSection({
  friendCode,
  visible,
}: Props) {

  const [items, setItems] =
    useState<WishlistItem[]>([]);

  useEffect(() => {
    if (!visible) {
      return;
    }

    fetch(
      `/api/friends/${
        encodeURIComponent(
          friendCode
        )
      }/wishlist`,
      {
        cache: "no-store",
      }
    )
      .then(async (response) => {
        if (!response.ok) {
          return [];
        }

        return response.json();
      })
      .then(setItems);
  }, [
    friendCode,
    visible,
  ]);

  if (!visible) {
    return null;
  }

  return (
    <section className="friendWishlistSection">
      <span className="eyebrowText">
        Gesucht
      </span>

      <h2>Wishlist</h2>

      {items.length === 0 ? (
        <p className="muted">
          Keine Karten auf der Wishlist.
        </p>
      ) : (
        <div className="friendWishlistGrid">
          {items.map((item) => {

            const image =
              item.imageBase
                ? `${item.imageBase.replace(/\/$/, "")}/high.webp`
                : null;

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
                className="friendWishlistCard"
                key={item.id}
              >
                {image ? (
                  <Image width={280} height={390} unoptimized
                    src={image}
                    alt={item.name}
                  />
                ) : (
                  <div className="cardImagePlaceholder" />
                )}

                <div>
                  <strong>
                    {item.name}
                  </strong>

                  <small>
                    {item.setName ??
                      "Unbekanntes Set"}
                    {" · #"}
                    {item.localId ?? "—"}
                  </small>

                  <div className="chips">
                    <span className="chip">
                      {item.languageCode.toUpperCase()}
                    </span>

                    {variant && (
                      <span className="chip">
                        {variant}
                      </span>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
