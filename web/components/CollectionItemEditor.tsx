"use client";

import {
  useEffect,
  useState,
} from "react";

import { EbayPriceHistoryChart } from "@/components/EbayPriceHistoryChart";

import type {
  PortfolioItem,
} from "@/lib/types";

import {
  singleValueEur,
} from "@/lib/pricing";

import {
  physicalVariantLabel,
} from "@/lib/variantLabel";

const CONDITIONS = [
  ["MINT", "Mint"],
  ["NEAR_MINT", "Near Mint"],
  ["EXCELLENT", "Excellent"],
  ["GOOD", "Good"],
  ["PLAYED", "Played"],
] as const;

type Market = "TCG" | "EBAY";

type EbayRecentSale = {
  itemId?: string | null;
  title: string;
  soldPriceEur: number;
  rawCondition?: string | null;
  endedAt?: string | null;
  url?: string | null;
};

type PricingQuote = {
  market?: Market | null;
  policyClass?: string | null;
  policyStatus?: string | null;
  source?: string | null;
  eur?: number | null;
  sampleCount?: number | null;
  rangeLowEur?: number | null;
  rangeHighEur?: number | null;
  referenceEur?: number | null;
  referenceNote?: string | null;
  recentSales?: EbayRecentSale[];
  priceWindowLabel?: string | null;
  lowSample?: boolean | null;
};

function nullableFiniteNumber(
  value: unknown
): number | null {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? parsed
    : null;
}

function variantLabel(
  item: PortfolioItem
) {
  const spec =
    item.variantSpec;

  if (!spec) {
    return item.variant;
  }

  return physicalVariantLabel(
    spec
  );
}

type Props = {
  item: PortfolioItem | null;
  market: Market;
  busy: boolean;
  displayedUnitEur?: number | null;
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
  displayedUnitEur,
  onClose,
  onSave,
  onDelete,
}: Props) {

  const [quantity, setQuantity] =
    useState(1);

  const [condition, setCondition] =
    useState("NEAR_MINT");

  const [selectedMarket, setSelectedMarket] =
    useState<Market>(market);

  const [pricingQuote, setPricingQuote] =
    useState<PricingQuote | null>(null);

  const [pricingLoading, setPricingLoading] =
    useState(false);

  const [pricingError, setPricingError] =
    useState<string | null>(null);

  const [ebaySales, setEbaySales] =
    useState<EbayRecentSale[]>([]);

  useEffect(() => {
    if (!item) return;

    setQuantity(
      item.quantity
    );

    setCondition(
      item.condition
    );

    setSelectedMarket(market);
    setPricingQuote(null);
    setPricingError(null);
    setEbaySales([]);
  }, [item, market]);

  useEffect(() => {
    if (!item) {
      return;
    }

    const controller =
      new AbortController();

    const params =
      new URLSearchParams({
        language: item.languageCode,
        condition,
        market: selectedMarket,
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

    setPricingLoading(true);
    setPricingError(null);
    setPricingQuote(null);

    if (selectedMarket !== "EBAY") {
      setEbaySales([]);
    }

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
              "Marktpreis konnte nicht geladen werden."
          );
        }

        const quote: PricingQuote = {
          market: data?.market === "TCG" || data?.market === "EBAY" ? data.market : null,
          policyClass: typeof data?.policyClass === "string" ? data.policyClass : null,
          policyStatus: typeof data?.policyStatus === "string" ? data.policyStatus : null,
          source:
            typeof data?.source === "string"
              ? data.source
              : null,
          eur:
            nullableFiniteNumber(
              data?.eur
            ),
          sampleCount:
            nullableFiniteNumber(
              data?.sampleCount
            ),
          rangeLowEur:
            nullableFiniteNumber(
              data?.rangeLowEur
            ),
          rangeHighEur:
            nullableFiniteNumber(
              data?.rangeHighEur
            ),
          referenceEur: nullableFiniteNumber(data?.referenceEur),
          referenceNote: typeof data?.referenceNote === "string" ? data.referenceNote : null,
          priceWindowLabel: typeof data?.priceWindowLabel === "string" ? data.priceWindowLabel : null,
          lowSample: data?.lowSample === true,
          recentSales:
            Array.isArray(data?.recentSales)
              ? data.recentSales
              : [],
        };

        setPricingQuote(quote);

        if (selectedMarket === "EBAY") {
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
        }
      })
      .catch((error) => {
        if (
          error instanceof DOMException &&
          error.name === "AbortError"
        ) {
          return;
        }

        setPricingQuote(null);
        setPricingError(
          error instanceof Error
            ? error.message
            : "Marktpreis konnte nicht geladen werden."
        );

        if (selectedMarket === "EBAY") {
          setEbaySales([]);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setPricingLoading(false);
        }
      });

    return () =>
      controller.abort();
  }, [
    item,
    selectedMarket,
    condition,
  ]);

  if (!item) {
    return null;
  }

  const currentItem = item;

  const storedUnitValue =
    condition === currentItem.condition
      ? singleValueEur(currentItem, selectedMarket)
      : null;

  const liveUnitValue =
    pricingQuote?.eur != null &&
    pricingQuote.eur > 0
      ? pricingQuote.eur
      : null;

  /*
   * eBay-Werte sind nur belastbar, wenn die API auch mindestens einen
   * konkreten Verkauf zurückliefert. Während der Abfrage und bei einer
   * reinen Zusammenfassung ohne Verkaufsdetails zeigen wir keinen alten
   * gespeicherten Wert und keinen unbestätigten Durchschnitt an.
   */
  // The collection overview is the source of truth for the value shown when
  // opening an unchanged item. A fresh quote is shown only for a changed
  // condition/market, preventing 0.02 € on the tile vs 0.06 € in the dialog.
  const effectiveMarket = pricingQuote?.market ?? selectedMarket;
  const redirectedBulkPrice = selectedMarket === "EBAY" &&
    pricingQuote?.market === "TCG" && pricingQuote.policyClass === "BULK";
  const showingCollectionValue =
    !redirectedBulkPrice && selectedMarket === market && condition === currentItem.condition;
  const unitValue = showingCollectionValue && displayedUnitEur !== undefined
    ? displayedUnitEur
    : effectiveMarket === "EBAY"
      ? pricingQuote !== null && ebaySales.length > 0 ? liveUnitValue : null
      : redirectedBulkPrice ? liveUnitValue : storedUnitValue ?? liveUnitValue;

  const positionValue =
    unitValue == null
      ? null
      : unitValue * quantity;

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
    if (busy || !Number.isInteger(quantity) || quantity < 1 || quantity > 100_000) return;
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
      onMouseDown={busy ? undefined : onClose}
    >
      <div
        className="editorModal"
        style={{
          maxHeight: "calc(100vh - 32px)",
          overflowY: "auto",
          overscrollBehavior: "contain",
        }}
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
            <span>Physische Variante</span>
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

        <div className="editorField">
          <span>Preismarkt</span>

          <div className="editorMarketSwitch">
            {(["TCG", "EBAY"] as const).map(
              (value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() =>
                    setSelectedMarket(value)
                  }
                  disabled={busy}
                  className={selectedMarket === value ? "selected" : ""}
                >
                  {value === "EBAY"
                    ? "eBay"
                    : "TCG"}
                </button>
              )
            )}
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
                    Math.min(100_000, quantity + 1)
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
            <span>
              {effectiveMarket === "EBAY"
                ? "eBay-Median pro Karte"
                : "TCG-Marktwert pro Karte"}
            </span>
            <strong>
              {pricingLoading && unitValue == null
                ? "Lädt …"
                : formatEur(unitValue)}
            </strong>
          </div>

          <div>
            <span>Positionswert</span>
            <strong>
              {pricingLoading && positionValue == null
                ? "Lädt …"
                : formatEur(positionValue)}
            </strong>
          </div>
        </div>

        {effectiveMarket === "TCG" && unitValue == null &&
          (pricingQuote?.referenceEur ?? item.referenceUnitEur ?? 0) > 0 && (
          <p style={{margin:"10px 0 0",color:"var(--secondary)",fontSize:13}}>
            Richtwert: {formatEur(pricingQuote?.referenceEur ?? item.referenceUnitEur ?? null)}
            {" "}pro Karte · Englisch · Druckvariante und Zustand ungeprüft.
            Nicht im Sammlungswert enthalten.
          </p>
        )}

        {redirectedBulkPrice && (
          <p style={{margin:"10px 0 0",color:"var(--secondary)",fontSize:12}}>
            Bulk-Karte: Für diese Variante wird der passende TCG-/Regionalmarktpreis genutzt.
            eBay ist nur für besondere Karten die reguläre Preisquelle.
          </p>
        )}
        {pricingQuote?.policyStatus && pricingQuote.policyStatus !== "PRICE_FOUND" && (
          <p style={{margin:"7px 0 0",color:"var(--secondary)",fontSize:12}}>
            Preisquelle noch nicht vollständig verifiziert: {pricingQuote.policyStatus}.
          </p>
        )}
        {pricingError && (
          <p
            style={{
              margin: "10px 0 0",
              color: "#ffb4df",
            }}
          >
            {pricingError}
          </p>
        )}

        {effectiveMarket === "EBAY" &&
          pricingQuote &&
          ebaySales.length > 0 && (
            <>
              <p
                style={{
                  margin: "10px 0 0",
                  color: "var(--secondary)",
                  fontSize: 12,
                }}
              >
                {pricingQuote.source === "CARDYSSEY_EBAY"
                  ? "CARDYSSEY eBay"
                  : pricingQuote.source ?? "eBay"}
                {pricingQuote.sampleCount != null
                  ? ` · ${pricingQuote.sampleCount} ${pricingQuote.sampleCount === 1 ? "Verkauf" : "Verkäufe"} · letzte 30 Tage`
                  : " · letzte 30 Tage"}
                {pricingQuote.rangeLowEur != null &&
                pricingQuote.rangeHighEur != null
                  ? ` · ${formatEur(pricingQuote.rangeLowEur)} – ${formatEur(pricingQuote.rangeHighEur)}`
                  : ""}
              </p>

              <p
                style={{
                  margin: "5px 0 0",
                  color: "var(--secondary)",
                  fontSize: 11,
                  lineHeight: 1.45,
                }}
              >
                eBay-Median: passende Verkäufe im Zeitraum {pricingQuote.priceWindowLabel ?? "30 Tage"} (ohne Versand).
                {pricingQuote.lowSample || pricingQuote.sampleCount === 1 ? " · Geringe Datenbasis" : ""}
              </p>
            </>
          )}

        {selectedMarket === "EBAY" && (
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
              Die letzten 10 der Verkäufe, die in die Berechnung eingeflossen sind.
            </p>

            {pricingLoading && (
              <p>Verkäufe werden geladen …</p>
            )}

            {!pricingLoading &&
              !pricingError &&
              ebaySales.length === 0 && (
                <p style={{ color: "var(--secondary)" }}>
                  Keine passenden verkauften eBay-Angebote gefunden. Deshalb wird kein eBay-Marktwert angezeigt.
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
                    {href && (
                      <div
                        style={{
                          marginTop: 7,
                          color: "var(--cyan)",
                          fontSize: 12,
                          fontWeight: 800,
                        }}
                      >
                        Bei eBay öffnen ↗
                      </div>
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

        {effectiveMarket === "EBAY" && item.variantSpec?.id && (
          <EbayPriceHistoryChart cardId={item.cardId} language={item.languageCode} variantId={item.variantSpec.id}/>
        )}

        <div className="editorActions">
          {!busy && <a className="ghostButton" href={`/chat?shareCard=${encodeURIComponent(currentItem.cardId)}&language=${encodeURIComponent(currentItem.languageCode)}&collectionKey=${encodeURIComponent(currentItem.key)}`}>Karte teilen</a>}
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
