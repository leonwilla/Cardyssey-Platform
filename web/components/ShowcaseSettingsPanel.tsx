"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  PortfolioItem,
} from "@/lib/types";

import {
  singleValueEur,
} from "@/lib/pricing";

type ShowcaseItem = {
  collectionItemId: string;
  position: number;
  cardId: string;
  name: string;
  setName?: string | null;
  localId?: string | null;
  imageBase?: string | null;
  variant: string;
};

type Privacy = {
  showcaseSize: 5 | 10;
};

type ShowcaseSort =
  | "VALUE_DESC"
  | "VALUE_ASC"
  | "NAME_ASC"
  | "SET_ASC";

function showcaseValue(
  item: PortfolioItem
): number | null {
  const values = [
    singleValueEur(item, "TCG"),
    singleValueEur(item, "EBAY"),
  ].filter(
    (value): value is number =>
      value != null
  );

  return values.length > 0
    ? Math.max(...values)
    : null;
}

function eur(
  value: number | null
) {
  return value == null
    ? "Kein Preis"
    : new Intl.NumberFormat(
        "de-DE",
        {
          style: "currency",
          currency: "EUR",
        }
      ).format(value);
}

function imageUrl(
  base?: string | null
) {
  return base
    ? `${base.replace(/\/$/, "")}/high.webp`
    : null;
}

export function ShowcaseSettingsPanel() {

  const [collection, setCollection] =
    useState<PortfolioItem[]>([]);

  const [selected, setSelected] =
    useState<string[]>([]);

  const [maxSize, setMaxSize] =
    useState<5 | 10>(5);

  const [saving, setSaving] =
    useState(false);

  const [message, setMessage] =
    useState<string | null>(null);

  const [query, setQuery] =
    useState("");

  const [sort, setSort] =
    useState<ShowcaseSort>(
      "VALUE_DESC"
    );

  const [minimumValue, setMinimumValue] =
    useState(0);

  useEffect(() => {
    async function load() {

      const [
        collectionResponse,
        showcaseResponse,
        privacyResponse,
      ] = await Promise.all([
        fetch("/api/collection", {
          cache: "no-store",
        }),
        fetch("/api/showcase", {
          cache: "no-store",
        }),
        fetch("/api/privacy", {
          cache: "no-store",
        }),
      ]);

      if (collectionResponse.ok) {
        setCollection(
          await collectionResponse.json()
        );
      }

      if (showcaseResponse.ok) {
        const showcase =
          (await showcaseResponse.json()) as ShowcaseItem[];

        setSelected(
          showcase
            .sort(
              (a, b) =>
                a.position - b.position
            )
            .map(
              (item) =>
                item.collectionItemId
            )
        );
      }

      if (privacyResponse.ok) {
        const privacy =
          (await privacyResponse.json()) as Privacy;

        setMaxSize(
          privacy.showcaseSize
        );
      }
    }

    load();
  }, []);

  const selectable =
    useMemo(
      () =>
        collection.filter(
          (item) => item.id
        ),
      [collection]
    );

  const visibleSelectable =
    useMemo(() => {
      const needle =
        query
          .trim()
          .toLocaleLowerCase("de");

      const filtered =
        selectable.filter((item) => {
          const matchesSearch =
            !needle ||
            [
              item.name,
              item.setName,
              item.localId,
            ]
              .filter(Boolean)
              .join(" ")
              .toLocaleLowerCase("de")
              .includes(needle);

          const value =
            showcaseValue(item);

          const matchesValue =
            minimumValue <= 0 ||
            (
              value != null &&
              value >= minimumValue
            );

          return (
            matchesSearch &&
            matchesValue
          );
        });

      return [...filtered].sort(
        (left, right) => {
          if (
            sort === "NAME_ASC"
          ) {
            return left.name.localeCompare(
              right.name,
              "de"
            );
          }

          if (
            sort === "SET_ASC"
          ) {
            return (
              (
                left.setName ?? ""
              ).localeCompare(
                right.setName ?? "",
                "de"
              ) ||
              (
                left.localId ?? ""
              ).localeCompare(
                right.localId ?? "",
                "de",
                {
                  numeric: true,
                }
              )
            );
          }

          const leftValue =
            showcaseValue(left);
          const rightValue =
            showcaseValue(right);

          if (
            leftValue == null &&
            rightValue == null
          ) {
            return left.name.localeCompare(
              right.name,
              "de"
            );
          }

          if (leftValue == null) {
            return 1;
          }

          if (rightValue == null) {
            return -1;
          }

          return sort === "VALUE_ASC"
            ? leftValue - rightValue
            : rightValue - leftValue;
        }
      );
    }, [
      minimumValue,
      query,
      selectable,
      sort,
    ]);

  function toggle(id: string) {

    if (selected.includes(id)) {
      setSelected(
        selected.filter(
          (value) => value !== id
        )
      );
      return;
    }

    if (selected.length >= maxSize) {
      setMessage(
        `Dein Showcase ist auf Top ${maxSize} eingestellt.`
      );
      return;
    }

    setSelected([
      ...selected,
      id,
    ]);

    setMessage(null);
  }

  function move(
    index: number,
    direction: -1 | 1
  ) {
    const target =
      index + direction;

    if (
      target < 0 ||
      target >= selected.length
    ) {
      return;
    }

    const copy =
      [...selected];

    [
      copy[index],
      copy[target],
    ] = [
      copy[target],
      copy[index],
    ];

    setSelected(copy);
  }

  async function save() {
    setSaving(true);
    setMessage(null);

    const response =
      await fetch(
        "/api/showcase",
        {
          method: "PUT",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            collectionItemIds:
              selected,
          }),
        }
      );

    setSaving(false);

    setMessage(
      response.ok
        ? "Showcase gespeichert."
        : "Showcase konnte nicht gespeichert werden."
    );
  }

  return (
    <section className="showcaseSettings">
      <div>
        <span className="eyebrowText">
          Showcase
        </span>

        <h2>
          Deine Top {maxSize}
        </h2>

        <p className="muted">
          Wähle deine Lieblingskarten.
          Die Reihenfolge bestimmt die
          Position im Profil.
        </p>
      </div>

      {selected.length > 0 && (
        <div className="showcaseSelected">
          {selected.map(
            (id, index) => {

              const item =
                selectable.find(
                  (card) =>
                    card.id === id
                );

              if (!item) {
                return null;
              }

              const image =
                imageUrl(
                  item.imageBase
                );

              return (
                <div
                  className="showcaseSlot"
                  key={id}
                >
                  <span className="showcasePosition">
                    #{index + 1}
                  </span>

                  {image ? (
                    <img
                      src={image}
                      alt={item.name}
                    />
                  ) : (
                    <div className="cardImagePlaceholder" />
                  )}

                  <strong>
                    {item.name}
                  </strong>

                  <div className="showcaseMove">
                    <button
                      onClick={
                        () =>
                          move(
                            index,
                            -1
                          )
                      }
                      disabled={
                        index === 0
                      }
                    >
                      ←
                    </button>

                    <button
                      onClick={
                        () =>
                          move(
                            index,
                            1
                          )
                      }
                      disabled={
                        index ===
                        selected.length - 1
                      }
                    >
                      →
                    </button>
                  </div>
                </div>
              );
            }
          )}
        </div>
      )}

      <div className="showcasePickerHeading">
        <h3>
          Karten auswählen
        </h3>

        <span>
          {visibleSelectable.length} Karten
        </span>
      </div>

      <div className="showcasePickerControls">
        <input
          type="search"
          value={query}
          onChange={(event) =>
            setQuery(
              event.target.value
            )
          }
          placeholder="Karte, Set oder Nummer suchen …"
          aria-label="Showcase-Karten suchen"
        />

        <select
          value={minimumValue}
          onChange={(event) =>
            setMinimumValue(
              Number(event.target.value)
            )
          }
          aria-label="Showcase-Karten nach Mindestwert filtern"
        >
          <option value={0}>
            Alle Werte
          </option>
          <option value={10}>
            Ab 10 €
          </option>
          <option value={25}>
            Ab 25 €
          </option>
          <option value={50}>
            Ab 50 €
          </option>
          <option value={100}>
            Ab 100 €
          </option>
        </select>

        <select
          value={sort}
          onChange={(event) =>
            setSort(
              event.target.value as ShowcaseSort
            )
          }
          aria-label="Showcase-Karten sortieren"
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
          <option value="SET_ASC">
            Set und Kartennummer
          </option>
        </select>
      </div>

      {visibleSelectable.length === 0 && (
        <div className="statusPanel">
          Keine passende Karte gefunden.
        </div>
      )}

      <div className="showcasePicker">
        {visibleSelectable.map((item) => {

          const id = item.id!;
          const active =
            selected.includes(id);

          const image =
            imageUrl(
              item.imageBase
            );

          return (
            <button
              type="button"
              key={id}
              className={
                active
                  ? "showcasePick selected"
                  : "showcasePick"
              }
              onClick={
                () => toggle(id)
              }
            >
              <div>
                {image ? (
                  <img
                    src={image}
                    alt=""
                  />
                ) : (
                  <div className="cardImagePlaceholder" />
                )}
              </div>

              <span>
                <strong>
                  {item.name}
                </strong>

                <small>
                  {item.setName ??
                    "Unbekanntes Set"}
                  {item.localId
                    ? ` · #${item.localId}`
                    : ""}
                </small>

                <small className="showcasePickValue">
                  {eur(
                    showcaseValue(item)
                  )}
                </small>
              </span>

              <b>
                {active
                  ? "✓"
                  : "+"}
              </b>
            </button>
          );
        })}
      </div>

      {message && (
        <div className="statusPanel">
          {message}
        </div>
      )}

      <button
        className="primaryButton"
        onClick={save}
        disabled={saving}
      >
        {saving
          ? "Speichert …"
          : "Showcase speichern"}
      </button>
    </section>
  );
}
