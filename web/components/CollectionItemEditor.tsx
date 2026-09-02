"use client";

import {
  useEffect,
  useState,
} from "react";

import type {
  PortfolioItem,
} from "@/lib/types";

import {
  positionValueEur,
  singleValueEur,
} from "@/lib/pricing";

const CONDITIONS = [
  ["MINT", "Mint"],
  ["NEAR_MINT", "Near Mint"],
  ["EXCELLENT", "Excellent"],
  ["GOOD", "Good"],
  ["PLAYED", "Played"],
] as const;

function variantLabel(
  item: PortfolioItem
) {
  const spec =
    item.variantSpec;

  if (!spec) {
    return item.variant;
  }

  return [
    spec.type,
    spec.subtype,
    ...spec.stamps,
  ]
    .filter(Boolean)
    .join(" · ");
}

type Props = {
  item: PortfolioItem | null;
  market: "TCG" | "EBAY";
  busy: boolean;
  onClose: () => void;
  onSave:
    (
      item: PortfolioItem
    ) => Promise<void>;
  onDelete:
    (
      item: PortfolioItem
    ) => Promise<void>;
};

export function CollectionItemEditor({
  item,
  market,
  busy,
  onClose,
  onSave,
  onDelete,
}: Props) {

  const [quantity, setQuantity] =
    useState(1);

  const [condition, setCondition] =
    useState("NEAR_MINT");

  useEffect(() => {
    if (!item) return;

    setQuantity(
      item.quantity
    );

    setCondition(
      item.condition
    );
  }, [item]);

  if (!item) {
    return null;
  }

  const currentItem = item;

  const unitValue =
    singleValueEur(
      currentItem,
      market,
      condition
    );

  const positionValue =
    positionValueEur(
      currentItem,
      market,
      quantity,
      condition
    );

  const formatEur = (
    value: number | null
  ) =>
    value == null
      ? "—"
      : new Intl.NumberFormat(
          "de-DE",
          {
            style: "currency",
            currency: "EUR",
          }
        ).format(value);

  async function save() {
    await onSave({
      ...currentItem,
      quantity,
      condition,
    });
  }

  async function remove() {
    const confirmed =
      window.confirm(
        `${currentItem.name} wirklich aus deiner Sammlung entfernen?`
      );

    if (!confirmed) {
      return;
    }

    await onDelete(currentItem);
  }

  return (
    <div
      className="modalBackdrop"
      onMouseDown={onClose}
    >
      <div
        className="editorModal"
        onMouseDown={
          (event) =>
            event.stopPropagation()
        }
      >
        <div className="editorHeader">
          <div>
            <span className="eyebrowText">
              Karte bearbeiten
            </span>

            <h2>
              {item.name}
            </h2>

            <p>
              {item.setName ??
                "Unbekanntes Set"}
              {" · #"}
              {item.localId ?? "—"}
            </p>
          </div>

          <button
            className="iconButton"
            onClick={onClose}
            disabled={busy}
            aria-label="Schließen"
          >
            ×
          </button>
        </div>

        <div className="editorInfo">
          <div>
            <span>Variante</span>
            <strong>
              {variantLabel(item)}
            </strong>
          </div>

          <div>
            <span>Sprache</span>
            <strong>
              {item.languageCode
                .toUpperCase()}
            </strong>
          </div>
        </div>

        <label className="editorField">
          <span>Zustand</span>

          <select
            value={condition}
            onChange={
              (event) =>
                setCondition(
                  event.target.value
                )
            }
            disabled={busy}
          >
            {CONDITIONS.map(
              ([value, label]) => (
                <option
                  key={value}
                  value={value}
                >
                  {label}
                </option>
              )
            )}
          </select>
        </label>

        <div className="editorField">
          <span>Menge</span>

          <div className="quantityControl">
            <button
              type="button"
              onClick={
                () =>
                  setQuantity(
                    Math.max(
                      1,
                      quantity - 1
                    )
                  )
              }
              disabled={
                busy ||
                quantity <= 1
              }
            >
              −
            </button>

            <strong>
              {quantity}
            </strong>

            <button
              type="button"
              onClick={
                () =>
                  setQuantity(
                    quantity + 1
                  )
              }
              disabled={busy}
            >
              +
            </button>
          </div>
        </div>

        <div className="editorValuePanel">
          <div>
            <span>Marktwert pro Karte</span>
            <strong>
              {formatEur(unitValue)}
            </strong>
          </div>

          <div>
            <span>Positionswert</span>
            <strong>
              {formatEur(positionValue)}
            </strong>
          </div>
        </div>

        <div className="editorActions">
          <button
            className="dangerButton"
            onClick={remove}
            disabled={busy}
          >
            Löschen
          </button>

          <div>
            <button
              className="ghostButton"
              onClick={onClose}
              disabled={busy}
            >
              Abbrechen
            </button>

            <button
              className="primaryButton"
              onClick={save}
              disabled={busy}
            >
              {busy
                ? "Speichert …"
                : "Speichern"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
