"use client";

import Image from "next/image";

import {
  useCallback,
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
  PortfolioItem,
  User,
} from "@/lib/types";

type SaleListing = {
  id: string;
  collectionItemId: string;
  cardId: string;
  name: string;
  setName?: string | null;
  localId?: string | null;
  imageBase?: string | null;
  variant: string;
  condition: string;
  ownedQuantity: number;
  quantity: number;
  priceEur?: number | null;
  negotiable: boolean;
  status:
    | "ACTIVE"
    | "PAUSED"
    | "SOLD";
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

export default function SellingPage() {
  const router = useRouter();

  const [user, setUser] =
    useState<User | null>(null);

  const [collection, setCollection] =
    useState<PortfolioItem[]>([]);

  const [listings, setListings] =
    useState<SaleListing[]>([]);

  const [collectionItemId, setCollectionItemId] =
    useState("");

  const [quantity, setQuantity] =
    useState(1);

  const [price, setPrice] =
    useState("");

  const [negotiable, setNegotiable] =
    useState(true);

  const [message, setMessage] =
    useState<string | null>(null);

  const load = useCallback(async () => {
    const [
      me,
      collectionResponse,
      sellingResponse,
    ] = await Promise.all([
      fetch("/api/auth/me", {
        cache: "no-store",
      }),
      fetch("/api/collection", {
        cache: "no-store",
      }),
      fetch("/api/selling", {
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

    if (collectionResponse.ok) {
      setCollection(
        await collectionResponse.json()
      );
    }

    if (sellingResponse.ok) {
      setListings(
        await sellingResponse.json()
      );
    }
  }, [router]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  const availableCollection =
    useMemo(() => {
      const used =
        new Set(
          listings.map(
            (listing) =>
              listing.collectionItemId
          )
        );

      return collection.filter(
        (item) =>
          item.id &&
          !used.has(item.id)
      );
    }, [
      collection,
      listings,
    ]);

  const selectedCollectionItem =
    collection.find(
      (item) =>
        item.id === collectionItemId
    );

  async function createListing() {
    if (!collectionItemId) {
      setMessage(
        "Bitte zuerst eine Karte auswählen."
      );
      return;
    }

    const parsedPrice =
      price.trim() === ""
        ? null
        : Number(
            price.replace(",", ".")
          );

    if (
      parsedPrice != null &&
      (
        !Number.isFinite(parsedPrice) ||
        parsedPrice <= 0
      )
    ) {
      setMessage(
        "Bitte einen gültigen Preis eingeben."
      );
      return;
    }

    const response =
      await fetch("/api/selling", {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify({
          collectionItemId,
          quantity,
          priceEur: parsedPrice,
          negotiable,
        }),
      });

    if (!response.ok) {
      setMessage(
        "Verkaufsangebot konnte nicht erstellt werden."
      );
      return;
    }

    setCollectionItemId("");
    setQuantity(1);
    setPrice("");
    setNegotiable(true);
    setMessage(
      "Verkaufsangebot erstellt."
    );

    await load();
  }

  async function changeStatus(
    listing: SaleListing,
    status:
      | "ACTIVE"
      | "PAUSED"
      | "SOLD"
  ) {
    const response =
      await fetch(
        `/api/selling/${
          encodeURIComponent(
            listing.id
          )
        }`,
        {
          method: "PUT",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            collectionItemId:
              listing.collectionItemId,
            quantity:
              listing.quantity,
            priceEur:
              listing.priceEur ?? null,
            negotiable:
              listing.negotiable,
            status,
          }),
        }
      );

    if (response.ok) {
      setMessage(
        status === "SOLD"
          ? "Verkaufsangebot als verkauft markiert."
          : status === "PAUSED"
            ? "Verkaufsangebot pausiert."
            : "Verkaufsangebot aktiviert."
      );
      await load();
    } else {
      setMessage(
        "Status konnte nicht geändert werden."
      );
    }
  }

  async function remove(
    id: string
  ) {
    const response =
      await fetch(
        `/api/selling/${
          encodeURIComponent(id)
        }`,
        {
          method: "DELETE",
        }
      );

    if (response.ok) {
      setMessage(
        "Verkaufsangebot entfernt."
      );
      await load();
    } else {
      setMessage(
        "Verkaufsangebot konnte nicht entfernt werden."
      );
    }
  }

  return (
    <AppShell
      active="/selling"
      user={user}
    >
      <div className="pageHeader">
        <div>
          <span className="eyebrowText">
            Marketplace
          </span>

          <h1>Meine Verkäufe</h1>

          <p className="muted">
            Biete Karten aus deiner
            Sammlung zum Verkauf an.
          </p>
        </div>
      </div>

      <section className="sellingCreate">
        <h2>Karte anbieten</h2>

        <label className="editorField">
          <span>Karte</span>

          <select
            value={collectionItemId}
            onChange={(event) => {
              setCollectionItemId(
                event.target.value
              );
              setQuantity(1);
            }}
          >
            <option value="">
              Karte auswählen …
            </option>

            {availableCollection.map(
              (item) => (
                <option
                  key={item.id}
                  value={item.id ?? ""}
                >
                  {item.name}
                  {" · "}
                  {item.variant}
                  {" · "}
                  {item.condition}
                </option>
              )
            )}
          </select>
        </label>

        <div className="sellingFormGrid">
          <label className="editorField">
            <span>Menge</span>

            <input
              type="number"
              min={1}
              max={
                selectedCollectionItem
                  ?.quantity ?? 1
              }
              value={quantity}
              onChange={(event) =>
                setQuantity(
                  Math.max(
                    1,
                    Number(
                      event.target.value
                    )
                  )
                )
              }
            />

            {selectedCollectionItem && (
              <small className="muted">
                Du besitzt{" "}
                {selectedCollectionItem.quantity}
                ×
              </small>
            )}
          </label>

          <label className="editorField">
            <span>
              Preis pro Karte
            </span>

            <input
              inputMode="decimal"
              value={price}
              onChange={(event) =>
                setPrice(
                  event.target.value
                )
              }
              placeholder="z. B. 24,90"
            />

            <small className="muted">
              Leer = Preis auf Anfrage
            </small>
          </label>
        </div>

        <label className="sellingCheckbox">
          <input
            type="checkbox"
            checked={negotiable}
            onChange={(event) =>
              setNegotiable(
                event.target.checked
              )
            }
          />

          Preis ist verhandelbar
        </label>

        {message && (
          <div className="statusPanel">
            {message}
          </div>
        )}

        <button
          className="primaryButton"
          onClick={createListing}
        >
          Zum Verkauf anbieten
        </button>
      </section>

      <section className="sellingList">
        <div className="sectionTitle">
          <div>
            <span className="eyebrowText">
              Angebote
            </span>

            <h2>
              Deine Verkaufskarten
            </h2>
          </div>
        </div>

        {listings.length === 0 ? (
          <div className="statusPanel">
            Noch keine Karten zum Verkauf.
          </div>
        ) : (
          <div className="sellingGrid">
            {listings.map(
              (listing) => {
                const image =
                  imageUrl(
                    listing.imageBase
                  );

                return (
                  <article
                    className="saleCard"
                    key={listing.id}
                  >
                    <div className="saleCardImage">
                      {image ? (
                        <Image width={280} height={390} unoptimized
                          src={image}
                          alt={listing.name}
                        />
                      ) : (
                        <div className="cardImagePlaceholder" />
                      )}
                    </div>

                    <div className="saleCardBody">
                      <div className="saleCardHead">
                        <div>
                          <h3>
                            {listing.name}
                          </h3>

                          <p className="muted">
                            {listing.setName ??
                              "Unbekanntes Set"}
                            {" · #"}
                            {listing.localId ??
                              "—"}
                          </p>
                        </div>

                        <span
                          className={`saleStatus ${listing.status.toLowerCase()}`}
                        >
                          {listing.status ===
                          "ACTIVE"
                            ? "Aktiv"
                            : listing.status ===
                                "PAUSED"
                              ? "Pausiert"
                              : "Verkauft"}
                        </span>
                      </div>

                      <div className="chips">
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

                      <div className="salePrice">
                        {money(
                          listing.priceEur
                        )}

                        {listing.negotiable && (
                          <small>
                            verhandelbar
                          </small>
                        )}
                      </div>

                      <div className="friendActions">
                        {listing.status !==
                          "ACTIVE" && (
                          <button
                            className="ghostButton"
                            onClick={() =>
                              changeStatus(
                                listing,
                                "ACTIVE"
                              )
                            }
                          >
                            Aktivieren
                          </button>
                        )}

                        {listing.status ===
                          "ACTIVE" && (
                          <button
                            className="ghostButton"
                            onClick={() =>
                              changeStatus(
                                listing,
                                "PAUSED"
                              )
                            }
                          >
                            Pausieren
                          </button>
                        )}

                        {listing.status !==
                          "SOLD" && (
                          <button
                            className="ghostButton"
                            onClick={() => {
                              if (
                                window.confirm(
                                  "Angebot als verkauft markieren? Du kannst es später wieder aktivieren."
                                )
                              ) {
                                changeStatus(
                                  listing,
                                  "SOLD"
                                );
                              }
                            }}
                          >
                            Verkauft
                          </button>
                        )}

                        <button
                          className="ghostButton"
                          onClick={() => {
                            if (
                              window.confirm(
                                "Inserat dauerhaft entfernen? Die Karte bleibt in deiner Sammlung."
                              )
                            ) {
                              remove(
                                listing.id
                              );
                            }
                          }}
                        >
                          Entfernen
                        </button>
                      </div>
                    </div>
                  </article>
                );
              }
            )}
          </div>
        )}
      </section>
    </AppShell>
  );
}
