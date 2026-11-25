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
import "../deck.css";
import "./sets.css";

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

type SetLanguage =
  | "de"
  | "en"
  | "ja"
  | "ko"
  | "zh-cn"
  | "zh-tw";

const setLanguages: {
  code: SetLanguage;
  label: string;
}[] = [
  { code: "de", label: "Deutsch" },
  { code: "en", label: "Englisch" },
  { code: "ja", label: "Japanisch" },
  { code: "ko", label: "Koreanisch" },
  { code: "zh-cn", label: "Chinesisch (vereinfacht)" },
  { code: "zh-tw", label: "Chinesisch (traditionell)" },
];

function isSetLanguage(
  value: string | null
): value is SetLanguage {
  return setLanguages.some(
    (language) =>
      language.code === value
  );
}

type SetSort =
  | "newest"
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
    <div className="setsArt">
      <span className="setsArtFallback">
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

  const [language, setLanguage] =
    useState<SetLanguage>("de");

  const [progressFilter, setProgressFilter] =
    useState<ProgressFilter>("all");

  const [sort, setSort] =
    useState<SetSort>("newest");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [
          me,
          collection,
        ] = await Promise.all([
          fetch("/api/auth/me", {
            cache: "no-store",
          }),
          fetch("/api/collection", {
            cache: "no-store",
          }),
        ]);

        if (me.status === 401) {
          router.replace("/login");
          return;
        }

        if (cancelled) return;

        if (me.ok) {
          const currentUser =
            (await me.json()) as User;

          setUser(currentUser);

          const savedLanguage =
            window.localStorage.getItem(
              `cardyssey.sets.language.${currentUser.id}`
            );

          if (
            isSetLanguage(
              savedLanguage
            )
          ) {
            setLanguage(
              savedLanguage
            );
          }
        }

        if (collection.ok) {
          setItems(
            await collection.json()
          );
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

  useEffect(() => {
    let cancelled = false;

    async function loadCatalog() {
      try {
        const response =
          await fetch(
            `/api/sets?language=${encodeURIComponent(language)}`,
            {
              cache: "no-store",
            }
          );

        if (cancelled) return;

        if (!response.ok) {
          setCatalogError(true);
          return;
        }

        setCatalog(
          await response.json()
        );
        setCatalogError(false);
      } catch {
        if (!cancelled) {
          setCatalogError(true);
        }
      }
    }

    loadCatalog();

    return () => {
      cancelled = true;
    };
  }, [language]);

  function selectLanguage(
    nextLanguage: SetLanguage
  ) {
    setLanguage(nextLanguage);

    if (user) {
      window.localStorage.setItem(
        `cardyssey.sets.language.${user.id}`,
        nextLanguage
      );
    }
  }

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
        if (
          item.languageCode !==
          language
        ) {
          continue;
        }

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
    [catalog, items, language]
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

    // Catalog order is newest-first from /api/sets; keep it as the default.
    const chronologicalOrder = new Map(catalog.map((set, index) => [set.id, index]));
    return [...filtered].sort(
      (a, b) => {
        switch (sort) {
          case "newest":
            return (chronologicalOrder.get(a.id) ?? Number.MAX_SAFE_INTEGER) -
              (chronologicalOrder.get(b.id) ?? Number.MAX_SAFE_INTEGER);
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
    catalog,
    sort,
  ]);

  const ownedCards = sets.reduce((n, set) => n + set.ownedCount, 0);
  const closest = sets
    .filter((set) => set.ownedCount > 0 && progressRatio(set) < 1)
    .sort((a, b) => progressRatio(b) - progressRatio(a))[0];

  return (
    <AppShell active="/sets" user={loading ? undefined : user}>
      <div className="dk">
        <section className="dk-deck" aria-label="Set-Bibliothek">
          <div className="dk-deckGrid">
            <div>
              <span className="dk-eyebrow">Deine Sets</span>
              <h1 className="dk-title">Set-Bibliothek</h1>
              <p className="dk-sub">Jedes Set ein Ordner. Sieh auf einen Blick, wo du fast komplett bist und was noch fehlt.</p>
              <div className="dk-stats">
                <div className="dk-stat"><b>{loading ? "…" : sets.length}</b><span>Sets</span></div>
                <div className="dk-stat"><b>{loading ? "…" : counts.started}</b><span>begonnen</span></div>
                <div className="dk-stat"><b>{loading ? "…" : counts.complete}</b><span>komplett</span></div>
                <div className="dk-stat"><b>{loading ? "…" : ownedCards.toLocaleString("de-DE")}</b><span>verschiedene Karten</span></div>
              </div>
            </div>
            {closest && (
              <button type="button" className="setsNext" onClick={() => router.push(`/sets/${encodeURIComponent(closest.id)}?language=${encodeURIComponent(language)}`)}>
                <div className="dk-ring" style={{ "--p": Math.round(progressRatio(closest) * 100), "--s": "112px" } as React.CSSProperties}>
                  <div><b>{Math.round(progressRatio(closest) * 100)}%</b><span>{closest.ownedCount}/{totalCards(closest)}</span></div>
                </div>
                <div>
                  <span className="dk-eyebrow">Am nächsten dran</span>
                  <strong>{closest.name}</strong>
                  <small>Noch {totalCards(closest) - closest.ownedCount} Karten bis komplett →</small>
                </div>
              </button>
            )}
          </div>
        </section>

        <section className="dk-tools" aria-label="Suche und Filter">
          <div className="dk-toolRow">
            <label className="dk-search">
              <span aria-hidden="true">🔍</span>
              <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Set suchen …" aria-label="Set suchen" />
            </label>
            <label className="dk-pill">Sprache
              <select value={language} onChange={(event) => selectLanguage(event.target.value as SetLanguage)}>
                {setLanguages.map((option) => <option key={option.code} value={option.code}>{option.label}</option>)}
              </select>
            </label>
            <label className="dk-pill">Sortieren
              <select value={sort} onChange={(event) => setSort(event.target.value as SetSort)}>
                <option value="newest">Neueste zuerst</option>
                <option value="owned-first">Begonnene zuerst</option>
                <option value="progress-desc">Fortschritt hoch → niedrig</option>
                <option value="progress-asc">Fortschritt niedrig → hoch</option>
                <option value="name-asc">Name A → Z</option>
                <option value="name-desc">Name Z → A</option>
              </select>
            </label>
          </div>
          <div className="dk-toolRow">
            <div className="dk-seg" role="group" aria-label="Fortschritt">
              {([["all", "Alle", counts.all], ["started", "Begonnen", counts.started], ["unstarted", "Nicht begonnen", counts.unstarted], ["complete", "Komplett", counts.complete]] as const).map(([value, label, n]) => (
                <button key={value} type="button" className={progressFilter === value ? "on" : ""} onClick={() => setProgressFilter(value)}>{label}<b>{n}</b></button>
              ))}
            </div>
            {!loading && <span className="dk-count">{visibleSets.length} Treffer</span>}
          </div>
        </section>

        {catalogError && <div className="dk-note">Der vollständige Set-Katalog konnte gerade nicht geladen werden. Sets aus deiner Sammlung bleiben sichtbar.</div>}

        {loading ? (
          <div className="dk-empty">Sets werden geladen …</div>
        ) : visibleSets.length === 0 ? (
          <div className="dk-empty">Kein passendes Set gefunden.</div>
        ) : (
          <div className="setsGrid">
            {visibleSets.map((set) => {
              const total = totalCards(set);
              const percent = total > 0 ? Math.min(100, (set.ownedCount / total) * 100) : 0;
              const complete = total > 0 && set.ownedCount >= total;
              return (
                <button type="button" key={set.id}
                  className={"setsTile" + (complete ? " complete" : set.ownedCount === 0 ? " fresh" : "")}
                  onClick={() => router.push(`/sets/${encodeURIComponent(set.id)}?language=${encodeURIComponent(language)}`)}>
                  <div className="setsLogo"><SetArtwork set={set} /></div>
                  <div className="setsBody">
                    <span className="setsCode">{set.id}</span>
                    <strong className="setsName">{set.name}</strong>
                    <div className="setsBar"><i style={{ width: `${percent}%` }} /></div>
                    <div className="setsFoot">
                      <span><b>{set.ownedCount}</b>{total > 0 ? ` / ${total}` : " gesammelt"}</span>
                      <span>{complete ? "★ Komplett" : total > 0 ? `${percent.toLocaleString("de-DE", { maximumFractionDigits: 1 })} %` : ""}</span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
