"use client";

import {
  useEffect,
} from "react";

import {
  usePathname,
} from "next/navigation";

export type AppearanceTheme =
  | "OBSIDIAN_GOLD"
  | "MIDNIGHT_CYAN"
  | "ROYAL_VIOLET"
  | "EMERALD_MINT";

export const appearanceThemes: readonly {
  id: AppearanceTheme;
  name: string;
  description: string;
  colors: readonly [string, string, string];
}[] = [
  {
    id: "OBSIDIAN_GOLD",
    name: "Obsidian Gold",
    description: "Graphit, Gold und dezentes Scanner-Cyan.",
    colors: ["#E2BC70", "#5EDCEB", "#A88BE8"],
  },
  {
    id: "MIDNIGHT_CYAN",
    name: "Midnight Cyan",
    description: "Tiefes Nachtblau mit klarem Cyan.",
    colors: ["#55DDF6", "#7AA7F8", "#8DEBFF"],
  },
  {
    id: "ROYAL_VIOLET",
    name: "Royal Violet",
    description: "Dunkles Violett mit hellen Holo-Akzenten.",
    colors: ["#B895FF", "#D4C2FF", "#FF88C7"],
  },
  {
    id: "EMERALD_MINT",
    name: "Emerald Mint",
    description: "Dunkles Grün mit frischen Mint-Akzenten.",
    colors: ["#6EE7B7", "#5EEAD4", "#A7F3D0"],
  },
];

const storageKey =
  "cardyssey.appearance.theme";

export function isAppearanceTheme(
  value: unknown
): value is AppearanceTheme {
  return appearanceThemes.some(
    (theme) => theme.id === value
  );
}

export function applyAppearanceTheme(
  theme: AppearanceTheme
) {
  document.documentElement.dataset.theme =
    theme;

  window.localStorage.setItem(
    storageKey,
    theme
  );

  window.dispatchEvent(
    new CustomEvent(
      "cardyssey-theme-change",
      { detail: theme }
    )
  );
}

export function cachedAppearanceTheme():
  AppearanceTheme {
  const cached =
    window.localStorage.getItem(
      storageKey
    );

  return isAppearanceTheme(cached)
    ? cached
    : "OBSIDIAN_GOLD";
}

export function ThemeSync() {
  const pathname = usePathname();

  useEffect(() => {
    applyAppearanceTheme(
      cachedAppearanceTheme()
    );

    fetch("/api/appearance", {
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) return null;
        return response.json();
      })
      .then((settings) => {
        if (
          settings &&
          isAppearanceTheme(
            settings.theme
          )
        ) {
          applyAppearanceTheme(
            settings.theme
          );
        }
      })
      .catch(() => {
        // Der lokale Stand bleibt aktiv,
        // wenn Tiny kurz nicht erreichbar ist.
      });
  }, [pathname]);

  return null;
}
