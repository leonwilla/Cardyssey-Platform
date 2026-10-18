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
  priority?: "LOW" | "MEDIUM" | "HIGH";
  targetPriceEur?: number | null;
};

type Listing = {
  id: string;
  cardId: string;
  languageCode: string;
  name: string;
  setName?: string | null;
  localId?: string | null;
  priceEur?: number | null;
};

function cardImage(
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
    ? "—"
    : new Intl.NumberFormat(
        "de-DE",
        {
          style: "currency",
          currency: "EUR",
        }
      ).format(value);
}

function priorityLabel(
  value?: string
) {
  switch (value) {
    case "HIGH":
      return "Hohe Priorität";
    case "LOW":
      return "Niedrige Priorität";
    default:
      return "Mittlere Priorität";
  }
}

export default function WishlistPage() {
  const router = useRouter();

  const [user, setUser] =
    useState<User | null>(null);

  const [items, setItems] =
    useState<WishlistItem[]>([]);

  const [marketplace, setMarketplace] =
    useState<Listing[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [editing, setEditing] =
    useState<WishlistItem | null>(
      null
    );

  const [priority, setPriority] =
    useState<
      "LOW" | "MEDIUM" | "HIGH"
    >("MEDIUM");

  const [
    targetPrice,
    setTargetPrice,
  ] = useState("");

  async function load() {
    const [me, wishlist, market] =
      await Promise.all([
        fetch("/api/auth/me", {
          cache: "no-store",
        }),
        fetch("/api/wishlist", {
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

    if (wishlist.ok) {
      setItems(
        await wishlist.json()
      );
    }

    if (market.ok) {
      setMarketplace(
        await market.json()
      );
    }

    setLoading(false);
  }

  useEffect(() => {
    void Promise.resolve().then(load);
  }, []);

  const matches =
    useMemo(() => {
      const result =
        new Map<
          string,
          Listing
        >();

      for (const item of items) {
        const matching =
          marketplace
            .filter(
              (listing) =>
                listing.cardId ===
                  item.cardId &&
                listing.languageCode ===
                  item.languageCode &&
                (
                  !item.setName ||
                  listing.setName ===
                    item.setName
                ) &&
                (
                  !item.localId ||
                  listing.localId ===
                    item.localId
                )
            )
            .sort(
              (left, right) =>
                (
                  left.priceEur ??
                  Number.POSITIVE_INFINITY
                ) -
                (
                  right.priceEur ??
                  Number.POSITIVE_INFINITY
                )
            );

        if (matching[0]) {
          result.set(
            item.id,
            matching[0]
          );
        }
      }

      return result;
    }, [
      items,
      marketplace,
    ]);

  async function remove(id: string) {
    const response =
      await fetch(
        `/api/wishlist/${encodeURIComponent(id)}`,
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

  function openEditor(
    item: WishlistItem
  ) {
    setEditing(item);
    setPriority(
      item.priority ?? "MEDIUM"
    );
    setTargetPrice(
      item.targetPriceEur == null
        ? ""
        : String(
            item.targetPriceEur
          ).replace(".", ",")
    );
  }

  async function save() {
    if (!editing) return;

    const normalized =
      targetPrice
        .trim()
        .replace(",", ".");

    const parsed =
      normalized
        ? Number(normalized)
        : null;

    if (
      parsed != null &&
      (
        !Number.isFinite(parsed) ||
        parsed < 0
      )
    ) {
      return;
    }

    const response =
      await fetch(
        `/api/wishlist/${encodeURIComponent(editing.id)}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            priority,
            targetPriceEur:
              parsed,
          }),
        }
      );

    if (!response.ok) {
      return;
    }

    const updated =
      (await response.json()) as
        WishlistItem;

    setItems(
      items.map((item) =>
        item.id === updated.id
          ? updated
          : item
      )
    );

    setEditing(null);
  }

  const sortedItems =
    useMemo(
      () =>
        [...items].sort(
          (left, right) => {
            const rank = (
              value?: string
            ) =>
              value === "HIGH"
                ? 0
                : value === "LOW"
                  ? 2
                  : 1;

            return (
              rank(left.priority) -
                rank(right.priority) ||
              left.name.localeCompare(
                right.name,
                "de"
              )
            );
          }
        ),
      [items]
    );

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
            Priorisiere Wunschkarten,
            setze einen Zielpreis und
            erkenne passende
            Marketplace-Angebote direkt.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="statusPanel">
          Wishlist wird geladen …
        </div>
      ) : sortedItems.length === 0 ? (
        <div className="statusPanel">
          Deine Wishlist ist noch leer.
          Füge Karten über die Kartensuche hinzu.
        </div>
      ) : (
        <div className="wishlistGrid">
          {sortedItems.map((item) => {
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

            const match =
              matches.get(item.id);

            const targetReached =
              match?.priceEur != null &&
              item.targetPriceEur != null &&
              match.priceEur <=
                item.targetPriceEur;

            return (
              <article
                className={
                  targetReached
                    ? "wishlistCard wishlistHit"
                    : "wishlistCard"
                }
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
                  <div className="wishlistMetaRow">
                    <span
                      className={
                        `wishlistPriority ${(
                          item.priority ??
                          "MEDIUM"
                        ).toLowerCase()}`
                      }
                    >
                      {priorityLabel(
                        item.priority
                      )}
                    </span>

                    {item.targetPriceEur !=
                      null && (
                      <span className="wishlistTarget">
                        Ziel{" "}
                        {money(
                          item.targetPriceEur
                        )}
                      </span>
                    )}
                  </div>

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

                  {match && (
                    <div
                      className={
                        targetReached
                          ? "wishlistMarketHit reached"
                          : "wishlistMarketHit"
                      }
                    >
                      {targetReached
                        ? "✓ Zielpreis erreicht · "
                        : "Marketplace-Treffer · "}
                      {money(
                        match.priceEur
                      )}
                    </div>
                  )}
                </div>

                <div className="wishlistActions">
                  <button
                    className="ghostButton"
                    onClick={
                      () =>
                        openEditor(item)
                    }
                  >
                    Bearbeiten
                  </button>

                  <button
                    className="ghostButton"
                    onClick={
                      () =>
                        remove(item.id)
                    }
                  >
                    Entfernen
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {editing && (
        <div
          className="editorBackdrop"
          onClick={
            () => setEditing(null)
          }
        >
          <div
            className="editorModal wishlistEditor"
            onClick={
              (event) =>
                event.stopPropagation()
            }
          >
            <span className="eyebrowText">
              Wishlist
            </span>

            <h2>
              {editing.name}
            </h2>

            <label className="editorField">
              <span>Priorität</span>
              <select
                value={priority}
                onChange={
                  (event) =>
                    setPriority(
                      event.target.value as
                        | "LOW"
                        | "MEDIUM"
                        | "HIGH"
                    )
                }
              >
                <option value="LOW">
                  Niedrig
                </option>
                <option value="MEDIUM">
                  Mittel
                </option>
                <option value="HIGH">
                  Hoch
                </option>
              </select>
            </label>

            <label className="editorField">
              <span>
                Zielpreis in €
              </span>
              <input
                inputMode="decimal"
                value={targetPrice}
                onChange={
                  (event) =>
                    setTargetPrice(
                      event.target.value
                    )
                }
                placeholder="optional"
              />
            </label>

            <p className="muted">
              Cardyssey markiert passende
              Marketplace-Angebote automatisch.
            </p>

            <div className="editorActions">
              <button
                className="ghostButton"
                onClick={
                  () =>
                    setEditing(null)
                }
              >
                Abbrechen
              </button>

              <button
                className="primaryButton"
                onClick={save}
              >
                Speichern
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
