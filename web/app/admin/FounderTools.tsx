"use client";

import Link from "next/link";
import {
  useEffect,
  useState,
} from "react";

import type { User } from "@/lib/types";

export function FounderTools() {
  const [founder, setFounder] =
    useState(false);

  useEffect(() => {
    let cancelled = false;

    fetch("/api/auth/me", {
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) return null;
        return response.json() as Promise<User>;
      })
      .then((user) => {
        if (!cancelled) {
          setFounder(
            user?.role === "FOUNDER" ||
            user?.canFounder === true
          );
        }
      })
      .catch(() => {
        // Der normale Admin-Bereich bleibt auch bei
        // einem temporären Fehler vollständig nutzbar.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (!founder) return null;

  return (
    <Link
      href="/admin/registration"
      className="ghostButton"
      style={{
        position: "fixed",
        right: "18px",
        bottom: "18px",
        zIndex: 50,
        textDecoration: "none",
        boxShadow: "0 10px 30px rgba(0,0,0,.28)",
      }}
    >
      Registrierung verwalten
    </Link>
  );
}
