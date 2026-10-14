export type CardVariantSpec = {
  id: string;
  type: string;
  foil?: string | null;
  stamps: string[];
  size?: string | null;
  subtype?: string | null;
};

export type PortfolioItem = {
  id?: string | null;
  key: string;
  cardId: string;
  languageCode: string;
  name: string;
  setId?: string | null;
  setName?: string | null;
  localId?: string | null;
  imageBase?: string | null;
  imageLanguage?: string | null;
  variant: string;
  variantSpec?: CardVariantSpec | null;
  condition: string;
  quantity: number;
  unitEur?: number | null;
  unitUsd?: number | null;
  marketUnitEur: Record<string, number>;
  marketUpdatedAtMs?: Record<string, number>;
  marketSampleCount?: Record<string, number>;
  valuedUnitEur?: Record<string, number>;
  positionValueEur?: Record<string, number>;
  referenceUnitEur?: number | null;
  referenceSource?: string | null;
  referenceUpdatedAtMs?: number | null;
  referenceNote?: string | null;
};

export type UserRole =
  | "USER"
  | "ADMIN"
  | "FOUNDER";

export type User = {
  id: string;
  email: string;
  displayName?: string | null;
  avatarUrl?: string | null;
  friendCode: string;
  role?: UserRole;
  canAdmin?: boolean;
  canFounder?: boolean;
};
