import type {
  PortfolioItem,
} from "@/lib/types";

const CONDITION_FACTORS:
  Record<string, number> = {
    MINT: 1.00,
    NEAR_MINT: 0.92,
    EXCELLENT: 0.80,
    GOOD: 0.65,
    PLAYED: 0.45,
  };

export function conditionFactor(
  condition: string
): number {
  return (
    CONDITION_FACTORS[
      condition
    ] ?? 1
  );
}

export function baseValueEur(
  item: PortfolioItem,
  market: "TCG" | "EBAY"
): number | null {
  return (
    item.marketUnitEur?.[
      market
    ] ??
    (
      market === "TCG"
        ? item.unitEur
        : null
    )
  );
}

export function singleValueEur(
  item: PortfolioItem,
  market: "TCG" | "EBAY",
  condition = item.condition
): number | null {
  const base =
    baseValueEur(
      item,
      market
    );

  if (base == null) {
    return null;
  }

  return (
    base *
    conditionFactor(
      condition
    )
  );
}

export function positionValueEur(
  item: PortfolioItem,
  market: "TCG" | "EBAY",
  quantity = item.quantity,
  condition = item.condition
): number | null {
  const single =
    singleValueEur(
      item,
      market,
      condition
    );

  return single == null
    ? null
    : single * quantity;
}
