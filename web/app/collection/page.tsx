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

import {
  CardTile,
} from "@/components/CardTile";

import {
  CollectionItemEditor,
} from "@/components/CollectionItemEditor";

import {
  AddCardDialog,
} from "@/components/AddCardDialog";

import type {
  PortfolioItem,
  User,
} from "@/lib/types";

import {
  positionValueEur,
  singleValueEur,
} from "@/lib/pricing";

type CollectionSort =
  | "VALUE_DESC"
  | "VALUE_ASC"
  | "NAME_ASC"
  | "NAME_DESC"
  | "SET_ASC"
  | "QUANTITY_DESC"
  | "QUANTITY_ASC";

const collectionSortValues:
  CollectionSort[] = [
    "VALUE_DESC",
    "VALUE_ASC",
    "NAME_ASC",
    "NAME_DESC",
    "SET_ASC",
    "QUANTITY_DESC",
    "QUANTITY_ASC",
  ];

function isCollectionSort(
  value: string | null
): value is CollectionSort {
  return value != null &&
    collectionSortValues.includes(
      value as CollectionSort
    );
}

function eur(
  value: number | null
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

function ebayQuoteIdentity(
  item: PortfolioItem
) {
  return [
    item.cardId,
    item.languageCode,
    item.variantSpec?.id ??
      `legacy:${item.variant}`,
    item.condition,
  ].join("|");
}

function ebayQuoteUrl(
  item: PortfolioItem
) {
  const params =
    new URLSearchParams({
      language: item.languageCode,
      condition: item.condition,
      market: "EBAY",
    });

  if (item.variantSpec?.id) {
    params.set(
      "variantId",
      item.variantSpec.id
    );
  } else if (item.variant) {
    params.set(
      "variant",
      item.variant
    );
  }

  return `/api/pricing/cards/${
    encodeURIComponent(item.cardId)
  }?${params.toString()}`;
}

function collectionMarketStorageKey(
  userId: string
) {
  return `cardyssey.collection.market.${userId}`;
}

function collectionSortStorageKey(
  userId: string
) {
  return `cardyssey.collection.sort.${userId}`;
}

export default function CollectionPage() {

  const router =
    useRouter();

  const [market, setMarket] =
    useState<"TCG" | "EBAY">(
      "TCG"
    );

  const [sort, setSort] =
    useState<CollectionSort>(
      "VALUE_DESC"
    );

  const [items, setItems] =
    useState<PortfolioItem[]>([]);

  const [user, setUser] =
    useState<User | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [editing, setEditing] =
    useState<PortfolioItem | null>(
      null
    );

  const [adding, setAdding] =
    useState(false);

  const [scannerCardId, setScannerCardId] =
    useState<string | null>(null);

  const [scannerLanguage, setScannerLanguage] =
    useState("de");

  const [saving, setSaving] =
    useState(false);

  const [ebayLiveUnitEur, setEbayLiveUnitEur] =
    useState<Record<string, number | null>>({});

  const [ebayLoading, setEbayLoading] =
    useState(false);

  const [ebayLoadError, setEbayLoadError] =
    useState<string | null>(null);

  function selectMarket(
    nextMarket: "TCG" | "EBAY"
  ) {
    setMarket(nextMarket);

    if (user) {
      window.localStorage.setItem(
        collectionMarketStorageKey(
          user.id
        ),
        nextMarket
      );
    }
  }

  function selectSort(
    nextSort: CollectionSort
  ) {
    setSort(nextSort);

    if (user) {
      window.localStorage.setItem(
        collectionSortStorageKey(
          user.id
        ),
        nextSort
      );
    }
  }

  useEffect(() => {
    const params =
      new URLSearchParams(
        window.location.search
      );

    const cardId =
      params.get("addCard");

    if (cardId) {
      setScannerCardId(
        cardId
      );

      setScannerLanguage(
        params.get("language") ||
          "de"
      );

      setAdding(true);
    }
  }, []);

  function closeAddCard() {
    setAdding(false);
    setScannerCardId(null);

    if (
      window.location.search
        .includes("addCard=")
    ) {
      router.replace(
        "/collection"
      );
    }
  }

  async function loadCollection() {
    const response =
      await fetch(
        "/api/collection",
        {
          cache: "no-store",
        }
      );

    if (
      response.status === 401
    ) {
      router.replace(
        "/login"
      );

      return;
    }

    if (!response.ok) {
      throw new Error(
        "Sammlung konnte nicht geladen werden."
      );
    }

    const collection =
      (
        await response.json()
      ) as PortfolioItem[];

    setItems(collection);
  }

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const meResponse =
          await fetch(
            "/api/auth/me",
            {
              cache: "no-store",
            }
          );

        if (
          meResponse.status === 401
        ) {
          router.replace(
            "/login"
          );

          return;
        }

        if (!meResponse.ok) {
          throw new Error(
            "Account konnte nicht geladen werden."
          );
        }

        const currentUser =
          (
            await meResponse.json()
          ) as User;

        if (!cancelled) {
          setUser(
            currentUser
          );

          const savedMarket =
            window.localStorage.getItem(
              collectionMarketStorageKey(
                currentUser.id
              )
            );

          if (
            savedMarket === "TCG" ||
            savedMarket === "EBAY"
          ) {
            setMarket(
              savedMarket
            );
          }

          const savedSort =
            window.localStorage.getItem(
              collectionSortStorageKey(
                currentUser.id
              )
            );

          if (
            isCollectionSort(
              savedSort
            )
          ) {
            setSort(
              savedSort
            );
          }
        }

        const collectionResponse =
          await fetch(
            "/api/collection",
            {
              cache:
                "no-store",
            }
          );

        if (
          collectionResponse.status ===
          401
        ) {
          router.replace(
            "/login"
          );

          return;
        }

        if (
          !collectionResponse.ok
        ) {
          throw new Error(
            "Sammlung konnte nicht geladen werden."
          );
        }

        const collection =
          (
            await collectionResponse.json()
          ) as PortfolioItem[];

        if (!cancelled) {
          setItems(
            collection
          );
        }

      } catch (e) {

        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : "Unbekannter Fehler"
          );
        }

      } finally {

        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    if (
      market !== "EBAY" ||
      items.length === 0
    ) {
      return;
    }

    const controller =
      new AbortController();

    let cancelled = false;

    const storedValues:
      Record<string, number | null> = {};

    for (const item of items) {
      storedValues[item.key] =
        singleValueEur(
          item,
          "EBAY"
        );
    }

    setEbayLiveUnitEur(
      storedValues
    );
    setEbayLoadError(null);
    setEbayLoading(true);

    const grouped =
      new Map<
        string,
        {
          item: PortfolioItem;
          keys: string[];
        }
      >();

    for (const item of items) {
      const identity =
        ebayQuoteIdentity(item);

      const existing =
        grouped.get(identity);

      if (existing) {
        existing.keys.push(
          item.key
        );
      } else {
        grouped.set(
          identity,
          {
            item,
            keys: [item.key],
          }
        );
      }
    }

    async function loadEbayCollectionValues() {
      try {
        const groups =
          Array.from(
            grouped.values()
          );

        // Keep provider/cache pressure bounded. Duplicate collection
        // positions share one quote through ebayQuoteIdentity above.
        for (
          let offset = 0;
          offset < groups.length;
          offset += 3
        ) {
          const batch =
            groups.slice(
              offset,
              offset + 3
            );

          const results =
            await Promise.all(
              batch.map(
                async (group) => {
                  const response =
                    await fetch(
                      ebayQuoteUrl(
                        group.item
                      ),
                      {
                        signal:
                          controller.signal,
                        cache: "no-store",
                      }
                    );

                  if (!response.ok) {
                    return {
                      keys: group.keys,
                      unitEur: null,
                    };
                  }

                  const data =
                    await response.json();

                  const raw =
                    Number(data?.eur);

                  return {
                    keys: group.keys,
                    unitEur:
                      Number.isFinite(raw) &&
                      raw > 0
                        ? raw
                        : null,
                  };
                }
              )
            );

          if (cancelled) {
            return;
          }

          setEbayLiveUnitEur(
            (current) => {
              const next = {
                ...current,
              };

              for (
                const result of results
              ) {
                for (
                  const key of result.keys
                ) {
                  next[key] =
                    result.unitEur;
                }
              }

              return next;
            }
          );
        }
      } catch (e) {
        if (
          e instanceof DOMException &&
          e.name === "AbortError"
        ) {
          return;
        }

        if (!cancelled) {
          setEbayLoadError(
            e instanceof Error
              ? e.message
              : "eBay-Marktwerte konnten nicht geladen werden."
          );
        }
      } finally {
        if (!cancelled) {
          setEbayLoading(false);
        }
      }
    }

    loadEbayCollectionValues();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [
    market,
    items,
  ]);

  async function saveItem(
    item: PortfolioItem
  ) {
    setSaving(true);
    setError(null);

    try {
      const response =
        await fetch(
          `/api/collection/${
            encodeURIComponent(
              item.key
            )
          }`,
          {
            method: "PUT",
            headers: {
              "Content-Type":
                "application/json",
            },
            body:
              JSON.stringify(
                item
              ),
          }
        );

      if (!response.ok) {
        throw new Error(
          "Änderung konnte nicht gespeichert werden."
        );
      }

      await loadCollection();

      setEditing(null);

    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Speichern fehlgeschlagen."
      );

    } finally {
      setSaving(false);
    }
  }

  async function deleteItem(
    item: PortfolioItem
  ) {
    setSaving(true);
    setError(null);

    try {
      const response =
        await fetch(
          `/api/collection/${
            encodeURIComponent(
              item.key
            )
          }`,
          {
            method: "DELETE",
          }
        );

      if (
        response.status !==
          204 &&
        !response.ok
      ) {
        throw new Error(
          "Karte konnte nicht gelöscht werden."
        );
      }

      await loadCollection();

      setEditing(null);

    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Löschen fehlgeschlagen."
      );

    } finally {
      setSaving(false);
    }
  }

  const ebayPricedCount =
    useMemo(
      () =>
        items.filter(
          (item) =>
            ebayLiveUnitEur[
              item.key
            ] != null ||
            singleValueEur(
              item,
              "EBAY"
            ) != null
        ).length,
      [
        items,
        ebayLiveUnitEur,
      ]
    );

  const total =
    useMemo(() => {

      const values =
        items
          .map(
            (item) => {
              if (
                market === "EBAY"
              ) {
                const hasLive =
                  Object.prototype.hasOwnProperty.call(
                    ebayLiveUnitEur,
                    item.key
                  );

                const unit =
                  hasLive
                    ? ebayLiveUnitEur[
                        item.key
                      ]
                    : singleValueEur(
                        item,
                        "EBAY"
                      );

                return unit == null
                  ? null
                  : unit *
                      item.quantity;
              }

              return positionValueEur(
                item,
                market
              );
            }
          )
          .filter(
            (
              value
            ): value is number =>
              value != null
          );

      if (
        values.length === 0
      ) {
        return null;
      }

      return values.reduce(
        (sum, value) =>
          sum + value,
        0
      );

    }, [
      items,
      market,
      ebayLiveUnitEur,
    ]);

  const sortedItems =
    useMemo(() => {
      const collator =
        new Intl.Collator(
          "de",
          {
            numeric: true,
            sensitivity: "base",
          }
        );

      function valueFor(
        item: PortfolioItem
      ): number | null {
        if (market === "EBAY") {
          const hasLive =
            Object.prototype.hasOwnProperty.call(
              ebayLiveUnitEur,
              item.key
            );

          const unit =
            hasLive
              ? ebayLiveUnitEur[
                  item.key
                ]
              : singleValueEur(
                  item,
                  "EBAY"
                );

          return unit == null
            ? null
            : unit *
                item.quantity;
        }

        return positionValueEur(
          item,
          market
        );
      }

      function compareValue(
        left: number | null,
        right: number | null,
        descending: boolean
      ) {
        if (
          left == null &&
          right == null
        ) {
          return 0;
        }

        if (left == null) {
          return 1;
        }

        if (right == null) {
          return -1;
        }

        return descending
          ? right - left
          : left - right;
      }

      return items
        .map(
          (item, index) => ({
            item,
            index,
            value: valueFor(item),
          })
        )
        .sort(
          (left, right) => {
            let result = 0;

            switch (sort) {
              case "VALUE_DESC":
                result = compareValue(
                  left.value,
                  right.value,
                  true
                );
                break;

              case "VALUE_ASC":
                result = compareValue(
                  left.value,
                  right.value,
                  false
                );
                break;

              case "NAME_ASC":
                result = collator.compare(
                  left.item.name,
                  right.item.name
                );
                break;

              case "NAME_DESC":
                result = collator.compare(
                  right.item.name,
                  left.item.name
                );
                break;

              case "SET_ASC":
                result = collator.compare(
                  left.item.setName ||
                    left.item.setId ||
                    "",
                  right.item.setName ||
                    right.item.setId ||
                    ""
                );

                if (result === 0) {
                  result = collator.compare(
                    left.item.localId ||
                      "",
                    right.item.localId ||
                      ""
                  );
                }
                break;

              case "QUANTITY_DESC":
                result =
                  right.item.quantity -
                  left.item.quantity;
                break;

              case "QUANTITY_ASC":
                result =
                  left.item.quantity -
                  right.item.quantity;
                break;
            }

            if (result !== 0) {
              return result;
            }

            const byName =
              collator.compare(
                left.item.name,
                right.item.name
              );

            return byName !== 0
              ? byName
              : left.index -
                  right.index;
          }
        )
        .map(
          ({ item }) => item
        );
    }, [
      items,
      market,
      ebayLiveUnitEur,
      sort,
    ]);

  const count =
    items.reduce(
      (sum, item) =>
        sum + item.quantity,
      0
    );

  const setCount =
    new Set(
      items
        .map(
          (item) =>
            item.setId
        )
        .filter(Boolean)
    ).size;

  return (
    <AppShell
      active="/collection"
      user={user}
    >
      <section className="pageIntro">
        <div>
          <span className="eyebrowText">
            Meine Sammlung
          </span>

          <h1>
            Deine Sammlung
          </h1>

          <p>
            Karten, Mengen und Marktwerte
            zentral und synchron verwalten.
          </p>
        </div>

        <button
          className="primaryButton"
          onClick={
            () =>
              setAdding(true)
          }
        >
          + Karte hinzufügen
        </button>
      </section>

      {loading && (
        <div className="statusPanel">
          Sammlung wird aus
          Cardyssey geladen …
        </div>
      )}

      {error && (
        <div className="statusPanel errorPanel">
          {error}
        </div>
      )}

      {!loading &&
        !error && (
          <>
            <section className="statsGrid">
              <div className="statCard heroStat">
                <span>
                  Sammlungswert
                </span>

                <strong>
                  {market === "EBAY" &&
                  ebayLoading &&
                  total == null
                    ? "Lädt …"
                    : eur(total)}
                </strong>

                <div className="segmented">
                  <button
                    onClick={
                      () =>
                        selectMarket(
                          "TCG"
                        )
                    }
                    className={
                      market ===
                      "TCG"
                        ? "selected"
                        : ""
                    }
                  >
                    TCG
                  </button>

                  <button
                    onClick={
                      () =>
                        selectMarket(
                          "EBAY"
                        )
                    }
                    className={
                      market ===
                      "EBAY"
                        ? "selected"
                        : ""
                    }
                  >
                    eBay
                  </button>
                </div>

                {market === "EBAY" && (
                  <small>
                    {ebayLoading
                      ? `eBay-Werte werden geladen · ${ebayPricedCount}/${items.length} Einträge bewertet`
                      : `${ebayPricedCount}/${items.length} Einträge mit eBay-Marktwert`}
                  </small>
                )}

                {market === "EBAY" &&
                  ebayLoadError && (
                    <small>
                      {ebayLoadError}
                    </small>
                  )}
              </div>

              <div className="statCard">
                <span>Karten</span>
                <strong>
                  {count}
                </strong>
                <small>
                  inklusive Mengen
                </small>
              </div>

              <div className="statCard">
                <span>
                  Sets begonnen
                </span>
                <strong>
                  {setCount}
                </strong>
                <small>
                  deine Sammlung
                </small>
              </div>

              <div className="statCard">
                <span>
                  Einträge
                </span>
                <strong>
                  {items.length}
                </strong>
                <small>
                  serverseitig
                </small>
              </div>
            </section>

            <section className="sectionBlock collectionSection">
              <div className="sectionTitle">
                <div>
                  <span className="eyebrowText">
                    Synchronisiert
                  </span>

                  <h2>
                    Deine Karten
                  </h2>
                </div>

                <div className="collectionToolbar">
                  <label className="collectionSortControl">
                    <span>
                      Sortierung
                    </span>

                    <select
                      value={sort}
                      onChange={
                        (event) =>
                          selectSort(
                            event.target.value as CollectionSort
                          )
                      }
                    >
                      <option value="VALUE_DESC">
                        Wert: hoch → niedrig
                      </option>
                      <option value="VALUE_ASC">
                        Wert: niedrig → hoch
                      </option>
                      <option value="NAME_ASC">
                        Name: A → Z
                      </option>
                      <option value="NAME_DESC">
                        Name: Z → A
                      </option>
                      <option value="SET_ASC">
                        Set und Kartennummer
                      </option>
                      <option value="QUANTITY_DESC">
                        Menge: hoch → niedrig
                      </option>
                      <option value="QUANTITY_ASC">
                        Menge: niedrig → hoch
                      </option>
                    </select>
                  </label>

                  <span className="syncBadge">
                    ● Server verbunden
                  </span>
                </div>
              </div>

              {items.length ===
              0 ? (
                <div className="statusPanel">
                  Deine Sammlung
                  ist noch leer.
                </div>
              ) : (
                <div className="cardGrid">
                  {sortedItems.map(
                    (item) => {
                      const hasLiveEbay =
                        market === "EBAY" &&
                        Object.prototype.hasOwnProperty.call(
                          ebayLiveUnitEur,
                          item.key
                        );

                      return (
                        <CardTile
                          key={
                            item.id ||
                            item.key
                          }
                          item={item}
                          market={
                            market
                          }
                          liveUnitEur={
                            hasLiveEbay
                              ? ebayLiveUnitEur[
                                  item.key
                                ]
                              : undefined
                          }
                          onEdit={
                            setEditing
                          }
                        />
                      );
                    }
                  )}
                </div>
              )}
            </section>
          </>
        )}

      <CollectionItemEditor
        item={editing}
        market={market}
        busy={saving}
        onClose={
          () =>
            !saving &&
            setEditing(null)
        }
        onSave={saveItem}
        onDelete={deleteItem}
      />
      <AddCardDialog
        open={adding}
        busy={saving}
        initialCardId={scannerCardId}
        initialLanguage={scannerLanguage}
        onClose={closeAddCard}
        onAdded={
          async () => {
            await loadCollection();
          }
        }
      />

    </AppShell>
  );
}
