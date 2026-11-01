"use client";

import {
  useEffect,
  useMemo,
  useRef,
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

type CollectionFilterName =
  | "language"
  | "set"
  | "variant"
  | "condition";

function collectionFilterStorageKey(
  userId: string,
  name: CollectionFilterName
) {
  return `cardyssey.collection.filter.${name}.${userId}`;
}

export default function CollectionPage() {

  const router =
    useRouter();

  const lastForegroundRefresh = useRef(0);
  const foregroundRefreshInFlight = useRef(false);

  const [market, setMarket] =
    useState<"TCG" | "EBAY">(
      "TCG"
    );

  const [sort, setSort] =
    useState<CollectionSort>(
      "VALUE_DESC"
    );

  const [view, setView] = useState<"SETS" | "CARDS">("SETS");
  const [openedSet, setOpenedSet] = useState<string | null>(null);
  const [query, setQuery] =
    useState("");

  const [languageFilter, setLanguageFilter] =
    useState("");

  const [setFilter, setSetFilter] =
    useState("");

  const [variantFilter, setVariantFilter] =
    useState("");

  const [conditionFilter, setConditionFilter] =
    useState("");

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

  function persistFilter(
    name: CollectionFilterName,
    value: string
  ) {
    if (!user) return;

    const key =
      collectionFilterStorageKey(
        user.id,
        name
      );

    if (value) {
      window.localStorage.setItem(
        key,
        value
      );
    } else {
      window.localStorage.removeItem(
        key
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

          setLanguageFilter(
            window.localStorage.getItem(
              collectionFilterStorageKey(
                currentUser.id,
                "language"
              )
            ) || ""
          );
          setSetFilter(
            window.localStorage.getItem(
              collectionFilterStorageKey(
                currentUser.id,
                "set"
              )
            ) || ""
          );
          setVariantFilter(
            window.localStorage.getItem(
              collectionFilterStorageKey(
                currentUser.id,
                "variant"
              )
            ) || ""
          );
          setConditionFilter(
            window.localStorage.getItem(
              collectionFilterStorageKey(
                currentUser.id,
                "condition"
              )
            ) || ""
          );
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

  // The API is the shared source for Android and Web. Reconcile the
  // collection when users return from another tab/device. Do not replace
  // the current view while an editor is actively changing a card.
  useEffect(() => {
    async function refreshOnReturn() {
      if (document.visibilityState !== "visible" ||
          editing || adding || saving ||
          foregroundRefreshInFlight.current) return;

      const now = Date.now();
      if (now - lastForegroundRefresh.current < 15_000) return;
      lastForegroundRefresh.current = now;
      foregroundRefreshInFlight.current = true;
      try {
        await loadCollection();
      } catch {
        // Keep the last successfully loaded collection on network errors.
      } finally {
        foregroundRefreshInFlight.current = false;
      }
    }

    document.addEventListener("visibilitychange", refreshOnReturn);
    window.addEventListener("focus", refreshOnReturn);
    // Keep two open devices in sync while the collection page is visible.
    // The shared backend remains authoritative; no provider scraping here.
    const interval = window.setInterval(refreshOnReturn, 15_000);
    return () => {
      document.removeEventListener("visibilitychange", refreshOnReturn);
      window.removeEventListener("focus", refreshOnReturn);
      window.clearInterval(interval);
    };
  }, [editing, adding, saving]);

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

  const languageOptions =
    useMemo(
      () =>
        [...new Set(
          items.map(
            (item) =>
              item.languageCode
          )
        )].sort(),
      [items]
    );

  const setOptions =
    useMemo(() => {
      const values =
        new Map<string, string>();

      items
        .filter(
          (item) =>
            !languageFilter ||
            item.languageCode ===
              languageFilter
        )
        .forEach((item) => {
          const id =
            item.setId || "";
          if (id) {
            values.set(
              id,
              item.setName ||
                id
            );
          }
        });

      return [...values.entries()]
        .sort(
          (left, right) =>
            left[1].localeCompare(
              right[1],
              "de",
              {
                numeric: true,
                sensitivity: "base",
              }
            )
        );
    }, [
      items,
      languageFilter,
    ]);

  const variantOptions =
    useMemo(
      () =>
        [...new Set(
          items
            .map(
              (item) =>
                item.variant
            )
            .filter(Boolean)
        )].sort(),
      [items]
    );

  const conditionOptions =
    useMemo(
      () =>
        [...new Set(
          items
            .map(
              (item) =>
                item.condition
            )
            .filter(Boolean)
        )].sort(),
      [items]
    );

  const filteredItems =
    useMemo(() => {
      const normalizedQuery =
        query.trim().toLocaleLowerCase(
          "de"
        );

      return items.filter(
        (item) => {
          const matchesQuery =
            !normalizedQuery ||
            [
              item.name,
              item.setName,
              item.setId,
              item.localId,
              item.cardId,
            ]
              .filter(Boolean)
              .some(
                (value) =>
                  String(value)
                    .toLocaleLowerCase(
                      "de"
                    )
                    .includes(
                      normalizedQuery
                    )
              );

          return (
            matchesQuery &&
            (!languageFilter ||
              item.languageCode ===
                languageFilter) &&
            (!setFilter ||
              item.setId ===
                setFilter) &&
            (!variantFilter ||
              item.variant ===
                variantFilter) &&
            (!conditionFilter ||
              item.condition ===
                conditionFilter)
          );
        }
      );
    }, [
      items,
      query,
      languageFilter,
      setFilter,
      variantFilter,
      conditionFilter,
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

      return filteredItems
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
      filteredItems,
      market,
      ebayLiveUnitEur,
      sort,
    ]);

  const groupedSets = useMemo(() => {
    const groups = new Map<string, PortfolioItem[]>();
    for (const item of sortedItems) {
      const id = item.setId || "OTHER";
      groups.set(id, [...(groups.get(id) || []), item]);
    }
    return [...groups].map(([id, cards]) => ({
      id, cards, name: cards[0]?.setName || id,
      quantity: cards.reduce((n, card) => n + card.quantity, 0),
      total: cards.reduce((n, card) => n + (positionValueEur(card, market) ?? 0), 0)
    })).sort((a, b) => b.total - a.total);
  }, [sortedItems, market]);
  const visibleCards = view === "SETS" && openedSet
    ? groupedSets.find((group) => group.id === openedSet)?.cards ?? [] : sortedItems;

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

                  <h2>{view === "SETS" ? (openedSet
                    ? groupedSets.find((group) => group.id === openedSet)?.name
                    : "Deine Sets") : "Deine Karten"}</h2>
                </div>

                <div className="collectionToolbar">
                  <label className="collectionSortControl collectionSearchControl">
                    <span>Suche</span>
                    <input
                      type="search"
                      placeholder="Name, Set oder Nummer"
                      value={query}
                      onChange={(event) =>
                        setQuery(
                          event.target.value
                        )
                      }
                    />
                  </label>

                  <label className="collectionSortControl">
                    <span>Sprache</span>
                    <select
                      value={languageFilter}
                      onChange={(event) => {
                        const value =
                          event.target.value;
                        setLanguageFilter(
                          value
                        );
                        persistFilter(
                          "language",
                          value
                        );
                        setSetFilter("");
                        persistFilter(
                          "set",
                          ""
                        );
                      }}
                    >
                      <option value="">
                        Alle
                      </option>
                      {languageOptions.map(
                        (language) => (
                          <option
                            key={language}
                            value={language}
                          >
                            {language.toUpperCase()}
                          </option>
                        )
                      )}
                    </select>
                  </label>

                  <label className="collectionSortControl">
                    <span>Set</span>
                    <select
                      value={setFilter}
                      onChange={(event) => {
                        const value =
                          event.target.value;
                        setSetFilter(value);
                        persistFilter(
                          "set",
                          value
                        );
                      }}
                    >
                      <option value="">
                        Alle
                      </option>
                      {setOptions.map(
                        ([id, name]) => (
                          <option
                            key={id}
                            value={id}
                          >
                            {name}
                          </option>
                        )
                      )}
                    </select>
                  </label>

                  <label className="collectionSortControl">
                    <span>Variante</span>
                    <select
                      value={variantFilter}
                      onChange={(event) => {
                        const value =
                          event.target.value;
                        setVariantFilter(
                          value
                        );
                        persistFilter(
                          "variant",
                          value
                        );
                      }}
                    >
                      <option value="">
                        Alle
                      </option>
                      {variantOptions.map(
                        (variant) => (
                          <option
                            key={variant}
                            value={variant}
                          >
                            {variant}
                          </option>
                        )
                      )}
                    </select>
                  </label>

                  <label className="collectionSortControl">
                    <span>Zustand</span>
                    <select
                      value={conditionFilter}
                      onChange={(event) => {
                        const value =
                          event.target.value;
                        setConditionFilter(
                          value
                        );
                        persistFilter(
                          "condition",
                          value
                        );
                      }}
                    >
                      <option value="">
                        Alle
                      </option>
                      {conditionOptions.map(
                        (condition) => (
                          <option
                            key={condition}
                            value={condition}
                          >
                            {condition}
                          </option>
                        )
                      )}
                    </select>
                  </label>

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

                  {(query ||
                    languageFilter ||
                    setFilter ||
                    variantFilter ||
                    conditionFilter) && (
                    <button
                      type="button"
                      className="ghostButton"
                      onClick={() => {
                        setQuery("");
                        setLanguageFilter("");
                        setSetFilter("");
                        setVariantFilter("");
                        setConditionFilter("");
                        (
                          [
                            "language",
                            "set",
                            "variant",
                            "condition",
                          ] as CollectionFilterName[]
                        ).forEach(
                          (name) =>
                            persistFilter(
                              name,
                              ""
                            )
                        );
                      }}
                    >
                      Filter zurücksetzen
                    </button>
                  )}

                  <span className="syncBadge">
                    {sortedItems.length}/{items.length} Einträge · ● Server verbunden
                  </span>
                </div>
              </div>

              <div className="collectionViewBar">
                <button type="button" onClick={() => {setView("SETS");setOpenedSet(null);}}>Sets</button>
                <button type="button" onClick={() => {setView("CARDS");setOpenedSet(null);}}>Alle Karten</button>
                {view === "SETS" && openedSet && <button type="button" onClick={() => setOpenedSet(null)}>Zurück zu Sets</button>}
              </div>
              {items.length ===
              0 ? (
                <div className="statusPanel">
                  Deine Sammlung
                  ist noch leer.
                </div>
              ) : sortedItems.length ===
                0 ? (
                <div className="statusPanel">
                  Keine Karten für die aktuellen Filter gefunden.
                </div>
              ) : view === "SETS" && !openedSet ? (
                <div className="collectionSetGrid">
                  {groupedSets.map((group) => (
                    <button type="button" className="collectionSetCard" key={group.id} onClick={() => setOpenedSet(group.id)}>
                      <strong>{group.name}</strong>
                      <span>{group.cards.length} Einträge / {group.quantity} Karten</span>
                      <b>{eur(group.total)}</b>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="cardGrid">
                  {visibleCards.map(
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
