"use client";
import { useEffect } from "react";
import { usePathname } from "next/navigation";

export const previewThemeKey = "cardyssey.redesign.experimental";
export function PreviewThemeSync() {
  const pathname = usePathname();
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("design") === "preview") localStorage.setItem(previewThemeKey, "1");
    if (params.get("design") === "classic") localStorage.removeItem(previewThemeKey);
    const sync = () => {
      const enabled = pathname !== "/" && pathname !== "/preview-redesign" && localStorage.getItem(previewThemeKey) === "1";
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
