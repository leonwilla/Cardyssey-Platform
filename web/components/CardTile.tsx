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
  onEdit?: (
    item: PortfolioItem
  ) => void;
};

export function CardTile({
  item,
  market = "TCG",
  onEdit,
}: Props) {

  const image =
    imageUrl(item);

  const unitValue =
    singleValueEur(
      item,
      market
    );

  const positionValue =
    positionValueEur(
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
          <img
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
              {eur(positionValue)}
            </span>

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
