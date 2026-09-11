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

type EbayRecentSale = {
  itemId?: string | null;
  title: string;
  soldPriceEur: number;
  rawCondition?: string | null;
  endedAt?: string | null;
  url?: string | null;
};

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

  const [ebaySales, setEbaySales] =
    useState<EbayRecentSale[]>([]);

  const [ebaySalesLoading, setEbaySalesLoading] =
    useState(false);

  const [ebaySalesError, setEbaySalesError] =
    useState<string | null>(null);

  useEffect(() => {
    if (!item) return;

    setQuantity(
      item.quantity
    );

    setCondition(
      item.condition
    );
  }, [item]);

  useEffect(() => {
    if (!item || market !== "EBAY") {
      setEbaySales([]);
      setEbaySalesError(null);
      setEbaySalesLoading(false);
      return;
    }

    const controller =
      new AbortController();

    const params =
      new URLSearchParams({
        language: item.languageCode,
        condition,
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

    setEbaySalesLoading(true);
    setEbaySalesError(null);

    fetch(
      `/api/pricing/cards/${encodeURIComponent(item.cardId)}?${params.toString()}`,
      {
        signal: controller.signal,
        cache: "no-store",
      }
    )
      .then(async (response) => {
        const data =
          await response.json();

        if (!response.ok) {
          throw new Error(
            data?.error ??
              "eBay-Verkäufe konnten nicht geladen werden."
          );
        }

        const sales =
          Array.isArray(data?.recentSales)
            ? data.recentSales
                .filter(
                  (sale: EbayRecentSale) =>
                    sale &&
                    typeof sale.title === "string" &&
                    Number.isFinite(
                      Number(sale.soldPriceEur)
                    )
                )
                .slice(0, 10)
            : [];

        setEbaySales(sales);
      })
      .catch((error) => {
        if (
          error instanceof DOMException &&
          error.name === "AbortError"
        ) {
          return;
        }

        setEbaySales([]);
        setEbaySalesError(
          error instanceof Error
            ? error.message
            : "eBay-Verkäufe konnten nicht geladen werden."
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setEbaySalesLoading(false);
        }
      });

    return () =>
      controller.abort();
  }, [item, market, condition]);

  if (!item) {
    return null;
  }

  const currentItem = item;

  const unitValue =
    singleValueEur(
      currentItem,
      market
    );

  const positionValue =
    positionValueEur(
      currentItem,
      market
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

        {market === "EBAY" && (
          <div
            style={{
              marginTop: 18,
              padding: 14,
              border: "1px solid rgba(38,58,85,.7)",
              borderRadius: 13,
              background: "rgba(20,33,57,.35)",
            }}
          >
            <strong>
              Letzte verwendete eBay-Verkäufe
            </strong>

            <p
              style={{
                margin: "6px 0 12px",
                color: "var(--secondary)",
                fontSize: 12,
              }}
            >
              Zum Prüfen anklicken – öffnet das originale eBay-Angebot.
            </p>

            {ebaySalesLoading && (
              <p>Verkäufe werden geladen …</p>
            )}

            {ebaySalesError && (
              <p style={{ color: "#ffb4df" }}>
                {ebaySalesError}
              </p>
            )}

            {!ebaySalesLoading &&
              !ebaySalesError &&
              ebaySales.length === 0 && (
                <p style={{ color: "var(--secondary)" }}>
                  Noch keine gespeicherten Verkäufe für diesen Preis.
                </p>
              )}

            <div
              style={{
                display: "grid",
                gap: 8,
              }}
            >
              {ebaySales.map((sale, index) => {
                const href =
                  sale.url?.startsWith("https://")
                    ? sale.url
                    : sale.itemId
                      ? `https://www.ebay.de/itm/${sale.itemId}`
                      : null;

                const content = (
                  <>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 12,
                      }}
                    >
                      <strong style={{ color: "var(--gold)" }}>
                        {formatEur(Number(sale.soldPriceEur))}
                      </strong>
                      <span style={{ color: "var(--secondary)", fontSize: 12 }}>
                        {sale.endedAt?.slice(0, 10) ?? `#${index + 1}`}
                      </span>
                    </div>
                    <div style={{ marginTop: 4 }}>
                      {sale.title}
                    </div>
                    {sale.rawCondition && (
                      <small style={{ color: "var(--secondary)" }}>
                        {sale.rawCondition}
                      </small>
                    )}
                  </>
                );

                const style = {
                  display: "block",
                  padding: 10,
                  border: "1px solid rgba(38,58,85,.65)",
                  borderRadius: 10,
                  background: "rgba(8,15,27,.7)",
                  color: "var(--text)",
                  textDecoration: "none",
                } as const;

                return href ? (
                  <a
                    key={`${sale.itemId ?? index}-${sale.endedAt ?? ""}`}
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    style={style}
                  >
                    {content}
                  </a>
                ) : (
                  <div
                    key={`${sale.itemId ?? index}-${sale.endedAt ?? ""}`}
                    style={style}
                  >
                    {content}
                  </div>
                );
              })}
            </div>
          </div>
        )}

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
