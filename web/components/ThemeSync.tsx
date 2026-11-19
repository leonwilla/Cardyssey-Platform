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

  try { window.localStorage.setItem(storageKey, theme); } catch { /* Browser storage is optional. */ }

  window.dispatchEvent(
    new CustomEvent(
      "cardyssey-theme-change",
      { detail: theme }
    )
  );
}

export function cachedAppearanceTheme():
  AppearanceTheme {
  let cached: string | null = null;
  try { cached = window.localStorage.getItem(storageKey); } catch { /* Use the default palette. */ }

  return isAppearanceTheme(cached)
    ? cached
    : "OBSIDIAN_GOLD";
}

export type BrightnessMode = "light" | "dark";
const brightnessKey = "cardyssey.appearance.brightness";

export function cachedBrightness(): BrightnessMode {
  try { return window.localStorage.getItem(brightnessKey) === "dark" ? "dark" : "light"; }
  catch { return "light"; }
}

export function applyBrightness(mode: BrightnessMode) {
  document.documentElement.dataset.brightness = mode;
  try { window.localStorage.setItem(brightnessKey, mode); } catch { /* Keep the active choice for this page. */ }
  window.dispatchEvent(new Event("cardyssey-brightness-change"));
}

export function ThemeSync() {
  const pathname = usePathname();

  useEffect(() => {
    applyBrightness(cachedBrightness());
    // Stored choices from the retired storefront cannot reactivate its layout.
    try { window.localStorage.removeItem("cardyssey.businessShop.design"); } catch { /* No persisted layout to migrate. */ }
    const sync = () => {
      document.documentElement.dataset.brightness = cachedBrightness();
      document.documentElement.dataset.theme = cachedAppearanceTheme();
    };
    window.addEventListener("storage", sync);
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
        // Keep the locally selected palette while the API is unavailable.
      });
    return () => window.removeEventListener("storage", sync);
  }, [pathname]);

  return null;
}
