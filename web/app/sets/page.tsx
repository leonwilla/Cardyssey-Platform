"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/AppShell";
import type {
  PortfolioItem,
  User,
} from "@/lib/types";

type CatalogSet = {
  id: string;
  name: string;
  logo?: string | null;
  symbol?: string | null;
  officialCount: number;
  totalCount: number;
};

type SetProgress = CatalogSet & {
  ownedCount: number;
};

function imageUrl(
  value?: string | null
) {
  if (!value) return null;

  if (
    /\.(png|jpe?g|webp|svg)(\?.*)?$/i.test(
      value
    )
  ) {
    return value;
  }

  return `${value.replace(/\/$/, "")}.webp`;
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export default function SetsPage() {
  const router = useRouter();

  const [items, setItems] =
    useState<PortfolioItem[]>([]);

  const [catalog, setCatalog] =
    useState<CatalogSet[]>([]);

  const [user, setUser] =
    useState<User | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [catalogError, setCatalogError] =
    useState(false);

  const [query, setQuery] =
    useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [
          me,
          collection,
          sets,
        ] = await Promise.all([
          fetch("/api/auth/me", {
            cache: "no-store",
          }),
          fetch("/api/collection", {
            cache: "no-store",
          }),
          fetch(
            "/api/sets?language=de",
            {
              cache: "no-store",
            }
          ),
        ]);

        if (me.status === 401) {
          router.replace("/login");
          return;
        }

        if (cancelled) return;

        if (me.ok) {
          setUser(await me.json());
        }

        if (collection.ok) {
          setItems(
            await collection.json()
          );
        }

        if (sets.ok) {
          setCatalog(
            await sets.json()
          );
          setCatalogError(false);
        } else {
          setCatalogError(true);
        }
      } catch {
        if (!cancelled) {
          setCatalogError(true);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [router]);

  const sets = useMemo<
    SetProgress[]
  >(() => {
    const ownedBySet =
      new Map<
        string,
        Set<string>
      >();

    const collectionNames =
      new Map<string, string>();

    for (const item of items) {
      if (!item.setId) continue;

      if (
        !ownedBySet.has(item.setId)
      ) {
        ownedBySet.set(
          item.setId,
          new Set()
        );
      }

      ownedBySet
        .get(item.setId)!
        .add(item.cardId);

      if (item.setName) {
        collectionNames.set(
          item.setId,
          item.setName
        );
      }
    }

    const result =
      new Map<
        string,
        SetProgress
      >();

    for (const set of catalog) {
      result.set(set.id, {
        ...set,
        ownedCount:
          ownedBySet.get(set.id)
            ?.size ?? 0,
      });
    }

    /*
     * Falls ein Set in der Sammlung
     * existiert, vom Katalog aber
     * temporär nicht geliefert wird,
     * verlieren wir es nicht.
     */
    for (
      const [
        setId,
        owned,
      ] of ownedBySet
    ) {
      if (result.has(setId)) {
        continue;
      }

      result.set(setId, {
        id: setId,
        name:
          collectionNames.get(setId) ??
          setId,
        logo: null,
        symbol: null,
        officialCount: 0,
        totalCount: 0,
        ownedCount: owned.size,
      });
    }

    return [...result.values()].sort(
      (a, b) =>
        a.name.localeCompare(
          b.name,
          "de"
        )
    );
  }, [catalog, items]);

  const visibleSets =
    useMemo(() => {
      const needle =
        query
          .trim()
          .toLocaleLowerCase("de");

      if (!needle) return sets;

      return sets.filter((set) =>
        `${set.name} ${set.id}`
          .toLocaleLowerCase("de")
          .includes(needle)
      );
    }, [query, sets]);

  const collectedSets =
    sets.filter(
      (set) => set.ownedCount > 0
    ).length;

  return (
    <AppShell
      active="/sets"
      user={
        loading
          ? undefined
          : user
      }
    >
      <section className="pageIntro setCatalogIntro">
        <div>
          <span className="eyebrowText">
            Deine Sets
          </span>

          <h1>Set-Fortschritt</h1>

          <p>
            Alle Pokémon-Sets an einem
            Ort. Verfolge deinen
            Sammlungsfortschritt und
            öffne jedes Set vollständig.
          </p>
        </div>

        {!loading && (
          <div className="setCatalogSummary">
            <div>
              <strong>
                {sets.length}
              </strong>
              <span>Sets</span>
            </div>

            <div>
              <strong>
                {collectedSets}
              </strong>
              <span>begonnen</span>
            </div>
          </div>
        )}
      </section>

      <div className="setCatalogControls">
        <input
          type="search"
          value={query}
          onChange={(event) =>
            setQuery(
              event.target.value
            )
          }
          placeholder="Set suchen …"
          aria-label="Set suchen"
        />

        {!loading && (
          <span>
            {visibleSets.length} Treffer
          </span>
        )}
      </div>

      {catalogError && (
        <div className="statusPanel">
          Der vollständige Set-Katalog
          konnte gerade nicht geladen
          werden. Bereits bekannte Sets
          aus deiner Sammlung bleiben
          sichtbar.
        </div>
      )}

      {loading ? (
        <div className="statusPanel">
          Sets werden geladen …
        </div>
      ) : visibleSets.length === 0 ? (
        <div className="statusPanel">
          Kein passendes Set gefunden.
        </div>
      ) : (
        <div className="setCatalogGrid">
          {visibleSets.map((set) => {
            const total =
              set.officialCount > 0
                ? set.officialCount
                : set.totalCount;

            const percent =
              total > 0
                ? Math.min(
                    100,
                    (
                      set.ownedCount /
                      total
                    ) * 100
                  )
                : 0;

            const image =
              imageUrl(
                set.logo ||
                  set.symbol
              );

            return (
              <article
                key={set.id}
                className="setCatalogTile"
                onClick={() =>
                  router.push(
                    `/sets/${encodeURIComponent(
                      set.id
                    )}`
                  )
                }
              >
                <div className="setCatalogVisual">
                  <span className="setCatalogFallback">
                    {initials(set.name)}
                  </span>

                  {image && (
                    <img
                      src={image}
                      alt=""
                      loading="lazy"
                      onError={(
                        event
                      ) => {
                        event.currentTarget.style.display =
                          "none";
                      }}
                    />
                  )}
                </div>

                <div className="setCatalogBody">
                  <span className="eyebrowText">
                    {set.id}
                  </span>

                  <h3>
                    {set.name}
                  </h3>

                  <div className="setCatalogStats">
                    <strong>
                      {set.ownedCount}
                      {total > 0
                        ? ` / ${total}`
                        : ""}
                    </strong>

                    <span>
                      {total > 0
                        ? `${percent.toFixed(
                            1
                          )} %`
                        : `${set.ownedCount} gesammelt`}
                    </span>
                  </div>

                  <div className="setProgress">
                    <span
                      style={{
                        width:
                          `${percent}%`,
                      }}
                    />
                  </div>

                  <div className="setCatalogFoot">
                    <span>
                      Set öffnen
                    </span>

                    <strong>›</strong>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
