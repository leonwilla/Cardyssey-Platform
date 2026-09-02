"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import type { PortfolioItem, User } from "@/lib/types";

export default function SetsPage() {
  const router = useRouter();
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const me = await fetch("/api/auth/me");
      if (me.status === 401) {
        router.replace("/login");
        return;
      }

      const collection = await fetch("/api/collection");

      if (me.ok) setUser(await me.json());
      if (collection.ok) setItems(await collection.json());

      setLoading(false);
    }

    load();
  }, [router]);

  const sets = useMemo(() => {
    const grouped = new Map<
      string,
      { id: string; name: string; owned: Set<string> }
    >();

    for (const item of items) {
      if (!item.setId) continue;

      const current =
        grouped.get(item.setId) ?? {
          id: item.setId,
          name: item.setName ?? item.setId,
          owned: new Set<string>(),
        };

      current.owned.add(item.cardId);
      grouped.set(item.setId, current);
    }

    return [...grouped.values()].sort(
      (a, b) => a.name.localeCompare(b.name, "de")
    );
  }, [items]);

  return (
    <AppShell active="/sets" user={user}>
      <section className="pageIntro">
        <div>
          <span className="eyebrowText">Deine Sets</span>
          <h1>Set-Fortschritt</h1>
          <p>Sets aus deiner aktuellen Sammlung.</p>
        </div>
      </section>

      {loading ? (
        <div className="statusPanel">Sets werden geladen …</div>
      ) : (
        <div className="setGrid large">
          {sets.map((set) => (
            <article
              key={set.id}
              className="setTile interactiveCard"
              onClick={() =>
                router.push(`/sets/${encodeURIComponent(set.id)}`)
              }
            >
              <div className="setHead">
                <div>
                  <span className="eyebrowText">{set.id}</span>
                  <h3>{set.name}</h3>
                </div>

                <b>{set.owned.size} gesammelt</b>
              </div>

              <div className="setFoot">
                <span>Set öffnen</span>
                <strong>›</strong>
              </div>
            </article>
          ))}
        </div>
      )}
    </AppShell>
  );
}
