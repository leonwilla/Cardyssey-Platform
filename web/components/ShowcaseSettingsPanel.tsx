"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  PortfolioItem,
} from "@/lib/types";

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

      <h3>
        Karten auswählen
      </h3>

      <div className="showcasePicker">
        {selectable.map((item) => {

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
