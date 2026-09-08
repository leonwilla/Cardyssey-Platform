import type { PortfolioItem } from "@/lib/types";

type Market = "TCG" | "EBAY";

export function baseValueEur(
  item: PortfolioItem,
  market: Market
): number | null {
  return (
    item.marketUnitEur?.[market] ??
    (market === "TCG" ? item.unitEur : null)
  );
}

export function singleValueEur(
  item: PortfolioItem,
  market: Market
): number | null {
  return item.valuedUnitEur?.[market] ?? null;
}

export function positionValueEur(
  item: PortfolioItem,
  market: Market
): number | null {
  return item.positionValueEur?.[market] ?? null;
}
