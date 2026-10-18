import Link from "next/link";

export function SharedChatCard({ objectType, payload }: { objectType?: string | null; payload: unknown }) {
  if (!objectType) return null;
  let data: unknown = payload;
  if (typeof data === "string") {
    try { data = JSON.parse(data); } catch { data = null; }
  }
  if (objectType !== "CARD" || !data || typeof data !== "object" || Array.isArray(data)) {
    return <div className="chip">Geteilter Inhalt · {objectType}</div>;
  }
  const card = data as Record<string, unknown>;
  if (typeof card.cardId !== "string" || typeof card.name !== "string") {
    return <div className="chip">Geteilter Inhalt · {objectType}</div>;
  }
  const language = typeof card.languageCode === "string" && ["de", "en", "ja", "ko", "zh-cn", "zh-tw"].includes(card.languageCode) ? card.languageCode : "de";
  const details = [card.setName || card.setId, typeof card.localId === "string" ? "#" + card.localId : null, language.toUpperCase(), card.variant]
    .filter((value): value is string => typeof value === "string" && value.length > 0);
  return (
    <Link className="statusPanel" style={{ display: "block", marginTop: 6 }}
      href={`/collection?addCard=${encodeURIComponent(card.cardId)}&language=${encodeURIComponent(language)}`}>
      <strong>{card.name}</strong>
      <div className="muted">{details.join(" · ")}</div>
      <small>Karte ansehen / hinzufügen →</small>
    </Link>
  );
}
