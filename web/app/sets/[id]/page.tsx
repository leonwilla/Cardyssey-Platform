"use client";

import Image from "next/image";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import type { PortfolioItem, User } from "@/lib/types";

type SetCard = {
  id: string;
  localId: string;
  name: string;
  imageBase?: string | null;
};

type SetDetails = {
  id: string;
  name: string;
  officialCount: number;
  totalCount: number;
  cards: SetCard[];
};

export default function SetDetailsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedLanguage =
    searchParams.get("language") || "de";
  const language =
    ["de", "en", "ja", "ko", "zh-cn", "zh-tw"].includes(
      requestedLanguage
    )
      ? requestedLanguage
      : "de";

  const [user, setUser] = useState<User | null>(null);
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [set, setSet] = useState<SetDetails | null>(null);
  const [fallback, setFallback] = useState(false);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      if (controller.signal.aborted) return;
      setLoading(true);
      setSet(null);
      setItems([]);
      setFallback(false);
    });
    async function get(path: string) {
      try {
        const response = await fetch(path, { cache: "no-store", signal: controller.signal });
        return { status: response.status, data: response.ok ? await response.json() : null };
      } catch {
        return { status: 0, data: null };
      }
    }
    async function load() {
      const id = params.id;
      const [me, collection, details] = await Promise.all([
        get("/api/auth/me"),
        get("/api/collection"),
        get(`/api/sets/${encodeURIComponent(id)}?language=${encodeURIComponent(language)}`),
      ]);
      if (controller.signal.aborted) return;
      if ([me.status, collection.status, details.status].includes(401)) {
        router.replace("/login");
        return;
      }
      if (me.data) setUser(me.data);
      const collectionItems: PortfolioItem[] = Array.isArray(collection.data) ? collection.data : [];
      setItems(collectionItems);
      if (details.data && Array.isArray(details.data.cards)) {
        setSet(details.data);
      } else {
        const matching = collectionItems.filter(item => item.setId === id && item.languageCode === language);
        const first = matching[0];
        if (first) {
          const unique = new Map<string, SetCard>();
          for (const item of matching) {
            if (!unique.has(item.cardId)) unique.set(item.cardId, {
              id: item.cardId, localId: item.localId ?? "", name: item.name, imageBase: item.imageBase,
            });
          }
          setSet({ id, name: first.setName ?? id, officialCount: 0, totalCount: unique.size, cards: [...unique.values()] });
          setFallback(true);
        }
      }
      setLoading(false);
    }
    void load();
    return () => controller.abort();
  }, [params.id, router, language, retry]);

  const owned = useMemo(
    () =>
      new Set(
        items
          .filter(
            (item) =>
              item.languageCode === language
          )
          .map((item) => item.cardId)
      ),
    [items, language]
  );

  if (loading) {
    return (
      <AppShell active="/sets" user={user}>
        <div className="statusPanel">
          Set wird geladen …
        </div>
      </AppShell>
    );
  }

  if (!set) {
    return (
      <AppShell active="/sets" user={user}>
        <div className="statusPanel errorPanel">
          Keine Set-Daten verfügbar.
          <button className="ghostButton" onClick={() => setRetry(value => value + 1)}>Erneut versuchen</button>
        </div>
      </AppShell>
    );
  }

  const ownedCount =
    set.cards.filter((card) => owned.has(card.id)).length;

  const percent =
    set.officialCount > 0
      ? (ownedCount / set.officialCount) * 100
      : null;

  return (
    <AppShell active="/sets" user={user}>
      <section className="pageIntro">
        <div>
          <span className="eyebrowText">{set.id}</span>
          <h1>{set.name}</h1>

          {fallback ? (
            <p>
              {ownedCount} gesammelte Karten ·
              TCGdex aktuell nicht erreichbar
            </p>
          ) : (
            <p>
              {ownedCount} / {set.officialCount} Karten ·{" "}
              {percent?.toFixed(1)} %
            </p>
          )}
        </div>
      </section>

      {fallback && (
        <div className="statusPanel">
          Offline-/Cache-Modus: Es werden momentan nur
          Karten angezeigt, die bereits in deiner Sammlung
          gespeichert sind.
        </div>
      )}

      <div className="cardGrid">
        {set.cards.map((card) => {
          const isOwned = owned.has(card.id);

          const image = card.imageBase
            ? `${card.imageBase.replace(/\/$/, "")}/high.webp`
            : null;

          return (
            <button
              type="button"
              key={card.id}
              className={`cardTile setCardButton ${
                isOwned ? "ownedSetCard" : ""
              }`}
              onClick={() =>
                router.push(
                  `/collection?addCard=${encodeURIComponent(
                    card.id
                  )}&language=${encodeURIComponent(language)}`
                )
              }
              aria-label={`${card.name} zur Sammlung hinzufügen`}
            >
              <div className="cardImageWrap">
                {image ? (
                  <Image width={280} height={390} unoptimized
                    src={image}
                    alt={card.name}
                    className="cardImage"
                  />
                ) : (
                  <div className="cardImagePlaceholder" />
                )}
              </div>

              <div className="cardMeta">
                <strong>{card.name}</strong>

                <div className="muted">
                  #{card.localId || "—"}
                </div>

                <div className="chips">
                  <span className="chip">
                    {isOwned ? "✓ In Sammlung" : "Fehlt"}
                  </span>

                  <span className="chip setCardAction">
                    {isOwned
                      ? "+ Weiteres Exemplar"
                      : "+ Hinzufügen"}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </AppShell>
  );
}
