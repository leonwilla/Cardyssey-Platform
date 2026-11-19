// The same catalog rarity tiers as Android; card value never determines rarity.
const rarityKey = (value: string) => value.normalize("NFD").replace(/\p{M}+/gu, "").toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
const tiers: [number, string[]][] = [
  [10, ["Common", "Häufig", "C"]],
  [20, ["Uncommon", "Ungewöhnlich", "U"]],
  [30, ["Rare", "Selten", "R"]],
  [40, ["Holo Rare", "Rare Holo", "Holografisch Selten", "Selten, Holografisch"]],
  [50, ["Double rare", "Doppelselten", "Holo Rare V", "Holografisch Selten V", "RR", "Rare Holo EX", "Rare Holo GX"]],
  [55, ["Rare PRIME", "selten, Primus", "Rare Holo LV.X", "Selten, Holografisch LV.X", "LEGEND", "LEGENDE", "Prism Star"]],
  [60, ["Holo Rare VMAX", "Holografisch Selten VMAX", "Holo Rare VSTAR", "Holografisch Selten VSTAR", "Triple Rare", "RRR"]],
  [65, ["ACE SPEC Rare", "ASS-KLASSE", "Amazing Rare", "Atemberaubend", "Radiant Rare", "Selten, Strahlend", "Shiny rare", "Shiny rare V", "Shiny rare VMAX"]],
  [70, ["Ultra Rare", "Ultra Selten", "Full Art Trainer", "Vollkunsttrainer", "Shiny Ultra Rare", "ultraselten, Schillernd", "Super Rare", "SR", "Pikachu Rare"]],
  [80, ["Illustration rare", "Selten, Illustration", "Art Rare", "AR", "Character Rare", "CHR"]],
  [90, ["Special illustration rare", "Selten, besondere Illustration", "Special Art Rare", "SAR", "Character Super Rare", "CSR"]],
  [95, ["Mega Attack Rare", "MA"]],
  [100, ["Hyper rare", "Hyperselten", "Secret Rare", "Versteckt Selten", "Rare Secret", "Rainbow Rare", "Rare Rainbow", "Gold Rare"]],
  [110, ["Black White Rare", "Schwarz-Weiß Selten", "Futuristic Rare", "RGB Rare"]],
  [120, ["Mega Hyper Rare", "Mega Hyper Selten", "Mega Ultra Rare", "MHR"]],
];
const ranks = new Map(tiers.flatMap(([rank, aliases]) => aliases.map(alias => [rarityKey(alias), rank] as const)));

export function cardRarityRank(rarity?: string | null): number | null {
  return rarity ? ranks.get(rarityKey(rarity)) ?? null : null;
}

type RarityCard = { id: string; localId: string; rarity?: string | null };
export function compareCardRarity(a: RarityCard, b: RarityCard, rarestFirst = true): number {
  const aRank = cardRarityRank(a.rarity);
  const bRank = cardRarityRank(b.rarity);
  if ((aRank == null) !== (bRank == null)) return aRank == null ? 1 : -1;
  const tier = ((aRank ?? 0) - (bRank ?? 0)) * (rarestFirst ? -1 : 1);
  const aNumber = Number(a.localId.match(/[0-9]+/)?.[0] ?? Number.MAX_SAFE_INTEGER);
  const bNumber = Number(b.localId.match(/[0-9]+/)?.[0] ?? Number.MAX_SAFE_INTEGER);
  return tier || aNumber - bNumber || a.localId.localeCompare(b.localId) || a.id.localeCompare(b.id);
}
