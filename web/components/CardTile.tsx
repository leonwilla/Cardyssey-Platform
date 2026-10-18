import Image from "next/image";
import type {
  PortfolioItem,
} from "@/lib/types";

import {
  positionValueEur,
  singleValueEur,
} from "@/lib/pricing";

const conditionLabel:
  Record<string, string> = {
    MINT: "Mint",
    NEAR_MINT: "Near Mint",
    EXCELLENT: "Excellent",
    GOOD: "Good",
    PLAYED: "Played",
  };

function eur(
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

function imageUrl(
  item: PortfolioItem
) {
  if (!item.imageBase) {
    return null;
  }

  return `${
    item.imageBase.replace(
      /\/$/,
      ""
    )
  }/high.webp`;
}

type Props = {
  item: PortfolioItem;
  market?: "TCG" | "EBAY";
  liveUnitEur?: number | null;
  onEdit?: (
    item: PortfolioItem
  ) => void;
};

export function CardTile({
  item,
  market = "TCG",
  liveUnitEur,
  onEdit,
}: Props) {

  const image =
    imageUrl(item);

  const storedUnitValue =
    singleValueEur(
      item,
      market
    );

  const unitValue =
    liveUnitEur !== undefined
      ? liveUnitEur
      : storedUnitValue;

  const referencePrice =
    market === "TCG" && unitValue == null && item.referenceUnitEur != null &&
    Number.isFinite(item.referenceUnitEur) && item.referenceUnitEur > 0
      ? item.referenceUnitEur : null;

  const positionValue =
    liveUnitEur !== undefined
      ? liveUnitEur == null
        ? null
        : liveUnitEur * item.quantity
      : positionValueEur(
          item,
          market
        );

  return (
    <article
      className={
        onEdit
          ? "cardTile interactiveCard"
          : "cardTile"
      }
      onClick={
        () =>
          onEdit?.(item)
      }
    >
      <div className="cardImageWrap">
        {image ? (
          <Image width={280} height={390} unoptimized
            src={image}
            alt={item.name}
            className="cardImage"
          />
        ) : (
          <div className="cardImagePlaceholder" />
        )}

        <span className="qtyBadge">
          {item.quantity}×
        </span>
      </div>

      <div className="cardMeta">
        <div className="cardTitleRow">
          <strong>
            {item.name}
          </strong>

          <div className="cardPriceBlock">
            <span className="price">
              {market === "EBAY" &&
              positionValue == null
                ? "Keine Verkäufe"
                : eur(positionValue)}
            </span>

            {referencePrice != null && (
              <small title={item.referenceNote ?? "Variante und Zustand ungeprüft. Nicht im Sammlungswert enthalten."}>
                Richtwert: {eur(referencePrice)} / Karte · EN · ungeprüfte Druckvariante
              </small>
            )}

            {item.quantity > 1 &&
              unitValue != null && (
                <small>
                  {eur(unitValue)} / Karte
                </small>
              )}
          </div>
        </div>

        <div className="muted">
          #{item.localId ?? "—"}
          {" · "}
          {item.setName ??
            "Unbekanntes Set"}
        </div>

        <div className="chips">
          <span className="chip">
            {variantLabel(item)}
          </span>

          <span className="chip mutedChip">
            {conditionLabel[
              item.condition
            ] ??
              item.condition}
          </span>
        </div>

        {onEdit && (
          <div className="cardEditHint">
            Bearbeiten
          </div>
        )}
      </div>
    </article>
  );
}
