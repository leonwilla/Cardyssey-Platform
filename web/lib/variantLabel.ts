export type PhysicalVariantLike = {
  type: string;
  subtype?: string | null;
  foil?: string | null;
  size?: string | null;
  stamps?: string[] | null;
};

function key(value: string | null | undefined) {
  return (value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

const TYPE_LABELS: Record<string, string> = {
  normal: "Normal",
  holo: "Holo",
  reverse: "Reverse Holo",
  metal: "Metall",
  lenticular: "Lentikular",
  "first edition": "1. Auflage",
};

const SUBTYPE_LABELS: Record<string, string> = {
  shadowless: "Schattenlos",
  unlimited: "Unlimited",
  "1999 2000 copyright": "Copyright 1999–2000",
  "missing expansion symbol": "Fehlendes Set-Symbol",
  "gold border": "Goldrand",
  "missing hp": "Fehlende KP",
  "aoki error": "Aoki-Fehldruck",
  "1999 copyright": "Copyright 1999",
  "evolution box error": "Evolutionsbox-Fehldruck",
  "no holo error": "Ohne Holo (Fehldruck)",
  "d ink dot error": "D-Ink-Dot-Fehldruck",
  "energy symbol error": "Energie-Symbol-Fehldruck",
  "text error": "Text-Fehldruck",
  "shifted energy cost": "Verschobene Energiekosten",
  "japanese back": "Japanische Rückseite",
  "no e reader": "Ohne e-Reader",
  "rarity error": "Seltenheits-Fehldruck",
  cosmos: "Cosmos",
  "blue border": "Blauer Rand",
  glossy: "Glossy",
  "shadowless red cheek": "Schattenlos · rote Wangen",
  "2019 copyright": "Copyright 2019",
  "2020 copyright": "Copyright 2020",
  "nintedo error": "Nintedo-Fehldruck",
  "1995 1998 copyright": "Copyright 1995–1998",
  "no rarity": "Ohne Seltenheitssymbol",
  "missing retreat cost": "Fehlende Rückzugskosten",
  "phanphy error": "Phanphy-Fehldruck",
  "peelable ditto": "Abziehbares Ditto",
};

const FOIL_LABELS: Record<string, string> = {
  pokeball: "Poké Ball Foil",
  greatball: "Great Ball Foil",
  ultraball: "Ultra Ball Foil",
  masterball: "Master Ball Foil",
  gold: "Gold Foil",
  cosmos: "Cosmos Foil",
  galaxy: "Galaxy Foil",
  starlight: "Starlight Foil",
  energy: "Energy Foil",
  "cracked ice": "Cracked Ice Foil",
  mirror: "Mirror Foil",
  league: "League Foil",
  "player reward": "Player Reward Foil",
  "professor program": "Professor Program Foil",
  tinsel: "Tinsel Foil",
  loveball: "Love Ball Foil",
  friendball: "Friend Ball Foil",
  quickball: "Quick Ball Foil",
  "team rocket": "Team Rocket Foil",
  duskball: "Dusk Ball Foil",
  rainbow: "Rainbow Foil",
  glitter: "Glitter Foil",
};

const STAMP_LABELS: Record<string, string> = {
  "1st edition": "1. Auflage",
  "w promo": "W-Promo Stamp",
  "pre release": "Prerelease Stamp",
  "pokemon center": "Pokémon Center Stamp",
  "set logo": "Set-Logo Stamp",
  staff: "Staff Stamp",
  "pikachu tail": "Pikachu-Tail Stamp",
  wotc: "WotC Stamp",
  winner: "Winner Stamp",
  snowflake: "Snowflake Stamp",
  "trick or trade": "Trick-or-Trade Stamp",
  gamestop: "GameStop Stamp",
  "eb games": "EB Games Stamp",
  "professor program": "Professor Program Stamp",
  "player rewards program": "Player Rewards Stamp",
  "pokemon day": "Pokémon Day Stamp",
  "pokemon together": "Pokémon Together Stamp",
  "25th celebration": "25th Celebration Stamp",
  "30th pokeday": "30th Pokéday Stamp",
  judge: "Judge Stamp",
  champion: "Champion Stamp",
  finalist: "Finalist Stamp",
  "semi finalist": "Semi-Finalist Stamp",
  "quarter finalist": "Quarter-Finalist Stamp",
};

function genericLabel(value: string) {
  return value
    .trim()
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((token) => {
      const lower = token.toLowerCase();
      if (lower === "pokemon") return "Pokémon";
      if (lower === "wotc") return "WotC";
      if (lower === "eb") return "EB";
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    })
    .join(" ");
}

export function physicalVariantLabel(
  variant: PhysicalVariantLike
) {
  const typeKey = key(variant.type);
  const parts: string[] = [
    TYPE_LABELS[typeKey] ?? genericLabel(variant.type),
  ];

  const subtype = variant.subtype?.trim();
  if (subtype) {
    const subtypeKey = key(subtype);
    parts.push(
      SUBTYPE_LABELS[subtypeKey] ?? genericLabel(subtype)
    );
  }

  for (const stamp of variant.stamps ?? []) {
    const stampKey = key(stamp);
    parts.push(
      STAMP_LABELS[stampKey] ?? `${genericLabel(stamp)} Stamp`
    );
  }

  const foil = variant.foil?.trim();
  if (foil) {
    const foilKey = key(foil);
    parts.push(
      FOIL_LABELS[foilKey] ?? `${genericLabel(foil)} Foil`
    );
  }

  const sizeKey = key(variant.size);
  if (sizeKey === "jumbo") {
    parts.push("Jumbo");
  } else if (sizeKey && sizeKey !== "standard") {
    parts.push(genericLabel(variant.size ?? ""));
  }

  return Array.from(new Set(parts.filter(Boolean))).join(" · ");
}
