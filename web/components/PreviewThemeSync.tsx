"use client";
import { useEffect } from "react";
import { usePathname } from "next/navigation";

export const previewThemeKey = "cardyssey.appearance.brightness";
export type BrightnessMode = "light" | "dark";
export function cachedBrightness():BrightnessMode {
  const value=window.localStorage.getItem(previewThemeKey);
  return value==="light"||value==="1"?"light":"dark";
}
export function applyBrightness(mode:BrightnessMode){
  window.localStorage.setItem(previewThemeKey,mode);
  window.dispatchEvent(new Event("cardyssey-redesign-change"));
}
export function PreviewThemeSync() {
  const pathname = usePathname();
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("design") === "preview") localStorage.setItem(previewThemeKey, "light");
    if (params.get("design") === "classic") localStorage.setItem(previewThemeKey, "dark");
    const sync = () => {
      const enabled = pathname !== "/" && pathname !== "/preview-redesign" && cachedBrightness() === "light";
      document.body.classList.toggle("cardysseyAppPreview", enabled);
    };
    sync();
    window.addEventListener("cardyssey-redesign-change", sync);
    return () => {
      window.removeEventListener("cardyssey-redesign-change", sync);
      document.body.classList.remove("cardysseyAppPreview");
    };
  }, [pathname]);
  return null;
}
