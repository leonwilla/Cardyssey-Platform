"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Group = {
  setId: string; setName: string; languageCode: string; affectedCards: number;
  missingPrices: number; deferredPrices: number; providerErrors: number;
  missingCache: number; missingVariantCards: number;
};
type Card = {
  cardId: string; cardName: string; cardNumber: string; variantId: string | null;
  variant: string | null; reason: string; failureDetail: string | null; nextAttemptAt: string | null;
};
type Page = { total: number; offset: number; items: Card[] };
const LANGUAGES = [
  ["de", "Deutsch"], ["en", "Englisch"], ["ja", "Japanisch"], ["ko", "Koreanisch"],
  ["zh-cn", "Chinesisch (vereinfacht)"], ["zh-tw", "Chinesisch (traditionell)"],
];
const languageName = (code: string) => LANGUAGES.find(([value]) => value === code)?.[1] ?? code;
const REASONS: Record<string, string> = {
  NO_PRICE: "Kein gültiger Preis", NO_PUBLIC_PRICE: "Zurückgestellt", PROVIDER_ERROR: "Providerfehler",
  MISSING_CACHE: "Noch kein Preiseintrag", MISSING_VARIANTS: "Variantendaten fehlen",
};
const cell = { textAlign: "left" as const, padding: "12px 10px", borderBottom: "1px solid var(--border)" };

export function AdminPriceCoverage() {
  const detailRef = useRef<HTMLDivElement>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [language, setLanguage] = useState("");
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("");
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Group | null>(null);
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<Page | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      if (controller.signal.aborted) return;
      setLoading(true); setError(null); setGroups([]); setSelected(null); setPage(null); setMessage(null);
    });
    void (async () => {
      try {
        const params = new URLSearchParams();
        if (language) params.set("language", language);
        const response = await fetch(`/api/admin/price-coverage?${params}`, { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error();
        const data = await response.json() as { groups: Group[] };
        if (!controller.signal.aborted) setGroups(data.groups);
      } catch {
        if (!controller.signal.aborted) setError("Die Set-Übersicht konnte nicht geladen werden.");
      } finally { if (!controller.signal.aborted) setLoading(false); }
    })();
    return () => controller.abort();
  }, [language, revision]);

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    queueMicrotask(() => {
      if (controller.signal.aborted) return;
      setDetailsLoading(true); setPage(null); setDetailError(null); setMessage(null);
    });
    void (async () => {
      try {
        const params = new URLSearchParams({ language: selected.languageCode, setId: selected.setId, offset: String(offset) });
        const response = await fetch(`/api/admin/price-coverage/cards?${params}`, { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error();
        const data = await response.json() as Page;
        if (!controller.signal.aborted) setPage(data);
      } catch {
        if (!controller.signal.aborted) setDetailError("Die Kartenliste konnte nicht geladen werden.");
      } finally { if (!controller.signal.aborted) setDetailsLoading(false); }
    })();
    return () => controller.abort();
  }, [selected, offset]);

  useEffect(() => { if (selected) detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [selected]);

  const visible = useMemo(() => groups.filter(group =>
    `${group.setName} ${group.setId} ${languageName(group.languageCode)}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()) &&
    (kind !== "prices" || group.missingPrices > 0) && (kind !== "variants" || group.missingVariantCards > 0)
  ), [groups, search, kind]);
  const totals = visible.reduce((sum, group) => ({
    prices: sum.prices + group.missingPrices, cards: sum.cards + group.affectedCards,
    variants: sum.variants + group.missingVariantCards, deferred: sum.deferred + group.deferredPrices,
  }), { prices: 0, cards: 0, variants: 0, deferred: 0 });

  async function copy(text: string) {
    try { await navigator.clipboard.writeText(text); setMessage("In die Zwischenablage kopiert."); }
    catch { setMessage("Kopieren fehlgeschlagen. Bitte die Zwischenablage im Browser erlauben."); }
  }
  function copySummary() {
    void copy("Cardyssey – fehlende Preise nach Set und Sprache\n" +
      "Fehlende Preise sind Varianten; fehlende Variantendaten sind Katalogeinträge und können Duplikate enthalten.\n\n" +
      visible.map(g => `${g.setName} [${g.setId}] | ${languageName(g.languageCode)} (${g.languageCode}) | betroffene Karten: ${g.affectedCards} | fehlende Preise: ${g.missingPrices} | davon zurückgestellt: ${g.deferredPrices} | Providerfehler: ${g.providerErrors} | ohne Preiseintrag: ${g.missingCache} | ohne Variantendaten: ${g.missingVariantCards}`).join("\n"));
  }
  function copyPage() {
    if (!selected || !page) return;
    void copy(`Cardyssey – ${selected.setName} [${selected.setId}] | ${languageName(selected.languageCode)} (${selected.languageCode})\nEinträge ${offset + 1}–${offset + page.items.length} von ${page.total}\n\n` +
      page.items.map(c => `${c.cardName} | #${c.cardNumber} | ${c.variant ?? "Variantendaten fehlen"} | ${REASONS[c.reason] ?? c.reason} | Grund: ${c.failureDetail ?? "—"} | nächster Versuch: ${c.nextAttemptAt ?? "—"} | cardId=${c.cardId} | variantId=${c.variantId ?? "—"}`).join("\n"));
  }

  return <section className="sectionBlock" id="set-price-coverage">
    <div className="sectionTitle"><div><span className="eyebrowText">Katalog-Abdeckung</span><h2>Fehlende Preise nach Set &amp; Sprache</h2></div><span className="chip mutedChip">{visible.length} Set-/Sprachgruppen</span></div>
    <p>Wähle ein Set, um die betroffenen Karten zu sehen. Zurückgestellte Fälle sind enthalten. Ein vorhandener, älterer Preis zählt hier weiterhin als Preis.</p>
    <div className="filterRow" style={{ marginBottom: 16 }}>
      <input aria-label="Set suchen" placeholder="Setname oder Setcode suchen …" value={search} onChange={e => setSearch(e.target.value)} />
      <select aria-label="Sprache der Set-Übersicht" value={language} onChange={e => setLanguage(e.target.value)}><option value="">Alle Sprachen</option>{LANGUAGES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      <select aria-label="Art der Kataloglücke" value={kind} onChange={e => setKind(e.target.value)}><option value="">Alle Lücken</option><option value="prices">Sets mit fehlenden Preisen</option><option value="variants">Sets ohne Variantendaten</option></select>
      <button className="ghostButton" type="button" disabled={loading} onClick={() => setRevision(v => v + 1)}>Aktualisieren</button>
      <button className="primaryButton" type="button" disabled={loading || !visible.length} onClick={copySummary}>Übersicht kopieren</button>
    </div>
    {message && <div className="statusPanel" role="status">{message}</div>}
    {error && <div className="statusPanel" role="alert">{error}</div>}
    {!loading && !error && <>
      <div className="statsGrid">
        <div className="statCard"><span>Fehlende Preise</span><strong>{totals.prices.toLocaleString("de-DE")}</strong><small>Varianten · davon {totals.deferred} zurückgestellt</small></div>
        <div className="statCard"><span>Betroffene Karten</span><strong>{totals.cards.toLocaleString("de-DE")}</strong><small>Katalogeinträge im Filter</small></div>
        <div className="statCard"><span>Ohne Variantendaten</span><strong>{totals.variants.toLocaleString("de-DE")}</strong><small>separat · können Duplikate enthalten</small></div>
      </div>
      <div style={{ overflow: "auto", maxHeight: "48vh", marginTop: 16 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 800 }}>
          <thead><tr>{["Set", "Sprache", "Karten", "Fehlende Preise", "Zurückgestellt", "Ohne Variantendaten", ""].map((label, i) => <th key={i} scope="col" style={cell}>{label}</th>)}</tr></thead>
          <tbody>{visible.map(group => <tr key={`${group.languageCode}:${group.setId}`}>
            <td style={cell}><strong>{group.setName}</strong><br /><small>{group.setId}</small></td>
            <td style={cell}>{languageName(group.languageCode)}</td><td style={cell}>{group.affectedCards}</td><td style={cell}>{group.missingPrices}</td><td style={cell}>{group.deferredPrices}</td><td style={cell}>{group.missingVariantCards}</td>
            <td style={cell}><button className="ghostButton" type="button" aria-pressed={selected?.setId === group.setId && selected?.languageCode === group.languageCode} onClick={() => { setOffset(0); setSelected(group); }}>Karten ansehen</button></td>
          </tr>)}</tbody>
        </table>
        {!visible.length && <div className="statusPanel">Keine passenden Kataloglücken gefunden.</div>}
      </div>
    </>}
    {loading && <div className="statusPanel">Set-Übersicht wird geladen …</div>}
    {selected && <div ref={detailRef} style={{ marginTop: 24, scrollMarginTop: 24 }}>
      <div className="sectionTitle"><div><h3>{selected.setName} · {languageName(selected.languageCode)}</h3><small>{selected.setId} · fehlende Preise und Variantendaten</small></div><button className="ghostButton" type="button" onClick={() => setSelected(null)}>Schließen</button></div>
      {detailError && <div className="statusPanel" role="alert">{detailError}</div>}
      {detailsLoading && <div className="statusPanel">Karten werden geladen …</div>}
      {page && !detailsLoading && <>
        <div className="filterRow"><span>{page.total ? `${offset + 1}–${offset + page.items.length}` : "0"} von {page.total} Einträgen</span><button className="ghostButton" type="button" disabled={offset === 0} onClick={() => setOffset(v => Math.max(0, v - 100))}>Zurück</button><button className="ghostButton" type="button" disabled={offset + page.items.length >= page.total} onClick={() => setOffset(v => v + 100)}>Weiter</button><button className="primaryButton" type="button" disabled={!page.items.length} onClick={copyPage}>Seite kopieren</button></div>
        <div style={{ overflow: "auto", maxHeight: "55vh", marginTop: 12 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 800 }}><thead><tr>{["Karte", "Nummer", "Variante", "Status", "Grund", "Nächster Versuch"].map(label => <th key={label} scope="col" style={cell}>{label}</th>)}</tr></thead>
            <tbody>{page.items.map(card => <tr key={`${card.cardId}:${card.variantId ?? "missing"}`}><td style={cell}>{card.cardName}<br /><small>{card.cardId}</small></td><td style={cell}>{card.cardNumber}</td><td style={cell}>{card.variant ?? "—"}</td><td style={cell}>{REASONS[card.reason] ?? card.reason}</td><td style={{ ...cell, maxWidth: 360 }}>{card.failureDetail ?? "—"}</td><td style={cell}>{card.nextAttemptAt ? new Date(card.nextAttemptAt).toLocaleString("de-DE") : "—"}</td></tr>)}</tbody>
          </table>
        </div>
      </>}
    </div>}
  </section>;
}
