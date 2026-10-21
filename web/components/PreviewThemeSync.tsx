"use client";
import { useEffect } from "react";
import { usePathname } from "next/navigation";

/** Preview palette is opt-in in this browser tab, never enabled for other visitors. */
export function PreviewThemeSync() {
  const pathname = usePathname();
  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    if (query.get("design") === "preview") sessionStorage.setItem("cardyssey-redesign-preview", "1");
    if (query.get("design") === "classic") sessionStorage.removeItem("cardyssey-redesign-preview");
    const enabled = pathname !== "/" && pathname !== "/preview-redesign" && sessionStorage.getItem("cardyssey-redesign-preview") === "1";
    document.body.classList.toggle("cardysseyAppPreview", enabled);
    return () => document.body.classList.remove("cardysseyAppPreview");
  }, [pathname]);
  return null;
}
