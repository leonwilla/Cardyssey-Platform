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
import styles from "./sets.module.css";

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

type ProgressFilter =
  | "all"
  | "started"
  | "unstarted"
  | "complete";

type SetSort =
  | "owned-first"
  | "progress-desc"
  | "progress-asc"
  | "name-asc"
  | "name-desc";

function totalCards(set: CatalogSet) {
  return Math.max(
    set.officialCount || 0,
    set.totalCount || 0
  );
}

function progressRatio(set: SetProgress) {
  const total = totalCards(set);

  if (total <= 0) return 0;

  return Math.min(
    1,
    set.ownedCount / total
  );
}

function imageCandidates(
  value?: string | null,
  symbol = false
) {
  if (!value) return [] as string[];

  const clean = value.replace(/\/$/, "");

  if (
    /\.(png|jpe?g|webp|svg)(\?.*)?$/i.test(
      clean
    )
  ) {
    return [clean];
  }

  return symbol
    ? [
        `${clean}.webp`,
        `${clean}.png`,
        `${clean}.jpg`,
      ]
    : [
        `${clean}.png`,
        `${clean}.webp`,
        `${clean}.jpg`,
      ];
}

function setImageCandidates(set: CatalogSet) {
  return [
    ...new Set([
      ...imageCandidates(set.logo),
      ...imageCandidates(
        set.symbol,
        true
      ),
    ]),
  ];
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

function SetArtwork({
  set,
}: {
  set: CatalogSet;
}) {
  const candidates = useMemo(
    () => setImageCandidates(set),
    [set.logo, set.symbol]
  );

  const [candidateIndex, setCandidateIndex] =
    useState(0);

  useEffect(() => {
    setCandidateIndex(0);
  }, [set.id, candidates]);

  const src =
    candidates[candidateIndex];

  return (
    <div className="setCatalogVisual">
      <span className="setCatalogFallback">
        {initials(set.name)}
      </span>

      {src && (
        <img
          src={src}
          alt=""
          loading="lazy"
          onError={() =>
            setCandidateIndex(
              (current) => current + 1
            )
          }
        />
      )}
    </div>
  );
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

  const [progressFilter, setProgressFilter] =
    useState<ProgressFilter>("all");

  const [sort, setSort] =
    useState<SetSort>("owned-first");

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

  const sets = useMemo<SetProgress[]>(
    () => {
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

      return [...result.values()];
    },
    [catalog, items]
  );

  const counts = useMemo(() => {
    let started = 0;
    let complete = 0;

    for (const set of sets) {
      const total = totalCards(set);

      if (set.ownedCount > 0) {
        started += 1;
      }

      if (
        total > 0 &&
        set.ownedCount >= total
      ) {
        complete += 1;
      }
    }

    return {
      all: sets.length,
      started,
      unstarted:
        sets.length - started,
      complete,
    };
  }, [sets]);

  const visibleSets = useMemo(() => {
    const needle =
      query
        .trim()
        .toLocaleLowerCase("de");

    const filtered = sets.filter(
      (set) => {
        const total = totalCards(set);
        const isComplete =
          total > 0 &&
          set.ownedCount >= total;

        const matchesQuery =
          !needle ||
          `${set.name} ${set.id}`
            .toLocaleLowerCase("de")
            .includes(needle);

        if (!matchesQuery) {
          return false;
        }

        switch (progressFilter) {
          case "started":
            return (
              set.ownedCount > 0 &&
              !isComplete
            );

          case "unstarted":
            return set.ownedCount === 0;

          case "complete":
            return isComplete;

          default:
            return true;
        }
      }
    );

    const byName = (
      a: SetProgress,
      b: SetProgress
    ) =>
      a.name.localeCompare(
        b.name,
        "de"
      );

    return [...filtered].sort(
      (a, b) => {
        switch (sort) {
          case "progress-desc": {
            const diff =
              progressRatio(b) -
              progressRatio(a);

            return diff || byName(a, b);
          }

          case "progress-asc": {
            const diff =
              progressRatio(a) -
              progressRatio(b);

            return diff || byName(a, b);
          }

          case "name-desc":
            return -byName(a, b);

          case "name-asc":
            return byName(a, b);

          default: {
            const aStarted =
              a.ownedCount > 0 ? 1 : 0;
            const bStarted =
              b.ownedCount > 0 ? 1 : 0;

            if (aStarted !== bStarted) {
              return bStarted - aStarted;
            }

            const progressDiff =
              progressRatio(b) -
              progressRatio(a);

            return (
              progressDiff ||
              b.ownedCount -
                a.ownedCount ||
              byName(a, b)
            );
          }
        }
      }
    );
  }, [
    query,
    progressFilter,
    sets,
    sort,
  ]);

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

          <h1>Set-Bibliothek</h1>

          <p>
            Entdecken, sammeln und
            deinen Fortschritt auf
            einen Blick verfolgen.
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
                {counts.started}
              </strong>
              <span>begonnen</span>
            </div>
          </div>
        )}
      </section>

      <section className={styles.filterPanel}>
        <div className={styles.searchRow}>
          <input
            className={styles.searchInput}
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

          <label className={styles.sortWrap}>
            <span>Sortieren</span>
            <select
              value={sort}
              onChange={(event) =>
                setSort(
                  event.target.value as SetSort
                )
              }
            >
              <option value="owned-first">
                Begonnene zuerst
              </option>
              <option value="progress-desc">
                Fortschritt: hoch → niedrig
              </option>
              <option value="progress-asc">
                Fortschritt: niedrig → hoch
              </option>
              <option value="name-asc">
                Name: A → Z
              </option>
              <option value="name-desc">
                Name: Z → A
              </option>
            </select>
          </label>
        </div>

        <div className={styles.chips}>
          {(
            [
              [
                "all",
                `Alle ${counts.all}`,
              ],
              [
                "started",
                `Begonnen ${counts.started}`,
              ],
              [
                "unstarted",
                `Nicht begonnen ${counts.unstarted}`,
              ],
              [
                "complete",
                `Vollständig ${counts.complete}`,
              ],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={
                progressFilter === value
                  ? styles.chipActive
                  : styles.chip
              }
              onClick={() =>
                setProgressFilter(value)
              }
            >
              {label}
            </button>
          ))}

          {!loading && (
            <span className={styles.results}>
              {visibleSets.length} Treffer
            </span>
          )}
        </div>
      </section>

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
              totalCards(set);

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
                <SetArtwork set={set} />

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
