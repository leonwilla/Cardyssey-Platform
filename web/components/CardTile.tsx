import type { PortfolioItem } from "@/lib/types";
import { positionValueEur, singleValueEur } from "@/lib/pricing";

const conditionLabel: Record<string, string> = {
  MINT: "Mint",
  NEAR_MINT: "Near Mint",
  EXCELLENT: "Excellent",
  GOOD: "Good",
  PLAYED: "Played",
};

export function eur(value?: number | null) {
  return value == null
    ? "—"
    : new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(value);
}

export function variantLabel(item: PortfolioItem) {
  const spec = item.variantSpec;
  if (!spec) return item.variant;
  return [spec.type, spec.subtype, ...spec.stamps].filter(Boolean).join(" · ");
}

export function cardImageUrl(item: PortfolioItem, size: "high" | "low" = "high") {
  return item.imageBase ? `${item.imageBase.replace(/\/$/, "")}/${size}.webp` : null;
}

type Props = {
  item: PortfolioItem;
  market?: "TCG" | "EBAY";
  liveUnitEur?: number | null;
  onEdit?: (item: PortfolioItem) => void;
};

/** One collection card, standing upright like in a binder pocket. */
export function CardTile({ item, market = "TCG", liveUnitEur, onEdit }: Props) {
  const image = cardImageUrl(item);
  const unitValue = liveUnitEur !== undefined ? liveUnitEur : singleValueEur(item, market);
  const referencePrice =
    market === "TCG" && unitValue == null && item.referenceUnitEur != null &&
    Number.isFinite(item.referenceUnitEur) && item.referenceUnitEur > 0
      ? item.referenceUnitEur : null;
  const positionValue =
    liveUnitEur !== undefined
      ? liveUnitEur == null ? null : liveUnitEur * item.quantity
      : positionValueEur(item, market);
  const variant = variantLabel(item);
  const holo = /holo|reverse|foil/i.test(variant);

  return (
    <article
      className="cx-card"
      role={onEdit ? "button" : undefined}
      tabIndex={onEdit ? 0 : undefined}
      aria-label={onEdit ? `${item.name} bearbeiten` : undefined}
      onClick={() => onEdit?.(item)}
      onKeyDown={(e) => { if (onEdit && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onEdit(item); } }}
    >
      <div className="cx-cardArt">
        {image ? <img src={image} alt={item.name} loading="lazy" /> : null}
        <span className="cx-qty">{item.quantity}×</span>
        <span className={"cx-price" + (positionValue == null ? " none" : "")}>
          {market === "EBAY" && positionValue == null ? "Keine Verkäufe" : eur(positionValue)}
        </span>
      </div>
      <div>
        <div className="cx-cardName" title={item.name}>{item.name}</div>
        <div className="cx-cardMeta" title={item.setName ?? undefined}>
          #{item.localId ?? "—"} · {item.setName ?? "Unbekanntes Set"}
        </div>
      </div>
      <div className="cx-tags">
        <span className={"cx-tag" + (holo ? " holo" : "")}>{variant}</span>
        <span className="cx-tag">{conditionLabel[item.condition] ?? item.condition}</span>
        <span className="cx-tag">{item.languageCode.toUpperCase()}</span>
      </div>
      {item.quantity > 1 && unitValue != null && <div className="cx-unit">{eur(unitValue)} / Karte</div>}
      {referencePrice != null && (
        <div className="cx-ref" title={item.referenceNote ?? "Variante und Zustand ungeprüft. Nicht im Sammlungswert enthalten."}>
          Richtwert {eur(referencePrice)} / Karte (EN, ungeprüft)
        </div>
      )}
    </article>
  );
}
