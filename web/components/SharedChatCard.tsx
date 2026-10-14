import Link from "next/link";

export function SharedChatCard({ objectType, payload }: { objectType?: string | null; payload: unknown }) {
  if (!objectType) return null;
  let data: any = payload;
  if (typeof data === "string") {
    try { data = JSON.parse(data); } catch { data = null; }
  }
  if (objectType !== "CARD" || !data || typeof data.cardId !== "string" || typeof data.name !== "string") {
    return <div className="chip">Geteilter Inhalt · {objectType}</div>;
  }
  const language = ["de", "en", "ja", "ko", "zh-cn", "zh-tw"].includes(data.languageCode) ? data.languageCode : "de";
  const details = [data.setName || data.setId, data.localId ? "#" + data.localId : null, language.toUpperCase(), data.variant]
    .filter(value => typeof value === "string" && value.length > 0);
  return (
    <Link className="statusPanel" style={{ display: "block", marginTop: 6 }}
      href={`/collection?addCard=${encodeURIComponent(data.cardId)}&language=${encodeURIComponent(language)}`}>
      <strong>{data.name}</strong>
      <div className="muted">{details.join(" · ")}</div>
      <small>Karte ansehen / hinzufügen →</small>
    </Link>
  );
}
