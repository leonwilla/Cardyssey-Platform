"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import type { PortfolioItem, User } from "@/lib/types";
import { positionValueEur } from "@/lib/pricing";
import "../../deck.css";
import "../sets.css";

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
  const [show, setShow] = useState<"all" | "owned" | "missing">("all");

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setSet(null);
    setItems([]);
    setFallback(false);
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

  const mine = useMemo(() => {
    const byCard = new Map<string, { quantity: number; value: number }>();
    for (const item of items) {
      if (item.languageCode !== language) continue;
      const entry = byCard.get(item.cardId) ?? { quantity: 0, value: 0 };
      entry.quantity += item.quantity;
      entry.value += positionValueEur(item, "TCG") ?? 0;
      byCard.set(item.cardId, entry);
    }
    return byCard;
  }, [items, language]);
  const owned = useMemo(() => new Set(mine.keys()), [mine]);

  if (loading || !set) {
    return (
      <AppShell active="/sets" user={user}>
        <div className="dk">
          {loading ? <div className="dk-empty">Set wird geladen …</div> : (
            <div className="dk-empty">Keine Set-Daten verfügbar. <button className="dk-ghost" onClick={() => setRetry((value) => value + 1)}>Erneut versuchen</button></div>
          )}
        </div>
      </AppShell>
    );
  }

  const ownedCount = set.cards.filter((card) => owned.has(card.id)).length;
  const total = set.officialCount > 0 ? set.officialCount : set.cards.length;
  const percent = total > 0 ? Math.min(100, (ownedCount / total) * 100) : 0;
  const setValue = set.cards.reduce((n, card) => n + (mine.get(card.id)?.value ?? 0), 0);
  const copies = set.cards.reduce((n, card) => n + (mine.get(card.id)?.quantity ?? 0), 0);
  const shown = set.cards.filter((card) => show === "all" || (show === "owned") === owned.has(card.id));
  const eur = (v: number) => v.toLocaleString("de-DE", { style: "currency", currency: "EUR" });
  const add = (id: string) => router.push(`/collection?addCard=${encodeURIComponent(id)}&language=${encodeURIComponent(language)}`);

  return (
    <AppShell active="/sets" user={user}>
      <div className="dk">
        <section className="dk-deck" aria-label={set.name}>
          <div className="dk-deckGrid">
            <div>
              <button type="button" className="setBack" onClick={() => router.push("/sets")}>← Set-Bibliothek</button>
              <span className="dk-eyebrow">{set.id} · {language.toUpperCase()}</span>
              <h1 className="dk-title">{set.name}</h1>
              <div className="dk-stats">
                <div className="dk-stat"><b>{ownedCount}{fallback ? "" : ` / ${total}`}</b><span>Karten gesammelt</span></div>
                <div className="dk-stat"><b>{fallback ? "–" : Math.max(0, total - ownedCount)}</b><span>fehlen noch</span></div>
                <div className="dk-stat"><b>{copies}</b><span>Exemplare</span></div>
                <div className="dk-stat"><b>{eur(setValue)}</b><span>Wert deiner Karten</span></div>
              </div>
            </div>
            {!fallback && (
              <div className="setRingWrap">
                <div className="dk-ring" style={{ "--p": Math.round(percent), "--s": "150px" } as React.CSSProperties}>
                  <div><b>{Math.round(percent)}%</b><span>{percent >= 100 ? "Komplett ★" : "komplett"}</span></div>
                </div>
              </div>
            )}
          </div>
        </section>

        {fallback && <div className="dk-note">Offline-Modus: Es werden nur Karten angezeigt, die schon in deiner Sammlung sind.</div>}

        <section className="dk-tools">
          <div className="dk-toolRow">
            <div className="dk-seg" role="group" aria-label="Anzeigen">
              {([["all", "Alle", set.cards.length], ["owned", "Habe ich", ownedCount], ["missing", "Fehlt", set.cards.length - ownedCount]] as const).map(([value, label, n]) => (
                <button key={value} type="button" className={show === value ? "on" : ""} onClick={() => setShow(value)}>{label}<b>{n}</b></button>
              ))}
            </div>
            <span className="dk-count">Fehlende Karte antippen = zur Sammlung hinzufügen</span>
          </div>
        </section>

        {shown.length === 0 ? (
          <div className="dk-empty">{show === "missing" ? "Nichts mehr offen – Set komplett! ★" : "Noch keine Karte aus diesem Set."}</div>
        ) : (
          <div className="dk-binder">
            {shown.map((card) => {
              const have = mine.get(card.id);
              const image = card.imageBase ? `${card.imageBase.replace(/\/$/, "")}/low.webp` : null;
              return (
                <button type="button" key={card.id} className={"dk-pocket" + (have ? "" : " missing")} onClick={() => add(card.id)}
                  aria-label={`${card.name} ${have ? "– weiteres Exemplar hinzufügen" : "zur Sammlung hinzufügen"}`}>
                  <div className="dk-art">
                    {image && <img src={image} alt={card.name} loading="lazy" />}
                    {have ? <span className="dk-badge gold">✓ {have.quantity}×</span> : <span className="dk-badge">#{card.localId || "—"}</span>}
                    <span className="dk-plus">{have ? "+ Weiteres Exemplar" : "+ Hinzufügen"}</span>
                  </div>
                  <div className="dk-name">{card.name}</div>
                  <div className="dk-meta">#{card.localId || "—"}{have && have.value > 0 ? ` · ${eur(have.value)}` : ""}</div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
