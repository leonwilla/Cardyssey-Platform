"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import type { User } from "@/lib/types";

type Entry = { id: number; name: string; set: string; number: string; language: string; variant: string; condition: string; price: string; quantity: string; image: string; notes: string; };
const blank = (id: number): Entry => ({ id, name: "", set: "", number: "", language: "Deutsch", variant: "Normal", condition: "Near Mint", price: "", quantity: "1", image: "", notes: "" });
const quote = (value: unknown) => '"' + String(value ?? "").replace(/"/g, '""').replace(/\r?\n/g, " ") + '"';
const slug = (text: string) => text.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,30);
const euros = (value: string) => Number(value.trim().replace(",", "."));

function makeCsv(rows: Entry[]) {
  const headings = ["Type","SKU","Name","Published","Is featured?","Visibility in catalog","Short description","Description","Tax status","In stock?","Stock","Backorders allowed?","Sold individually?","Regular price","Categories","Images","Attribute 1 name","Attribute 1 value(s)","Attribute 1 visible","Attribute 1 global","Attribute 2 name","Attribute 2 value(s)","Attribute 2 visible","Attribute 2 global","Attribute 3 name","Attribute 3 value(s)","Attribute 3 visible","Attribute 3 global"];
  const csv = rows.map((r) => {
    const title = [r.name.trim(), r.number.trim(), r.set.trim(), r.variant, r.language, r.condition].filter(Boolean).join(" · ");
    const sku = ["CDY",slug(r.set),slug(r.number),slug(r.name),slug(r.language),slug(r.variant),slug(r.condition)].join("-").toUpperCase();
    const brief = [r.set, r.number, r.language, r.variant, r.condition].filter(Boolean).join(" | ");
    const data = ["simple",sku,title,"0","0","visible",brief,r.notes,"taxable","1",r.quantity,"0","0",euros(r.price).toFixed(2),"Einzelkarten",r.image.trim(),"Sprache",r.language,"1","0","Variante",r.variant,"1","0","Zustand",r.condition,"1","0"];
    return data.map(quote).join(",");
  });
  return "\uFEFF" + [headings.map(quote).join(","), ...csv].join("\r\n") + "\r\n";
}

export default function ShopListingsPage() {
  const router = useRouter();
  const [allowed,setAllowed] = useState(false);
  const [checking,setChecking] = useState(true);
  const [rows,setRows] = useState<Entry[]>([blank(1)]);
  const [error,setError] = useState("");
  useEffect(() => {
    fetch("/api/auth/me", { cache:"no-store" }).then(async res => {
      if (res.status === 401) { router.replace("/login"); return; }
      if (!res.ok) throw new Error("Session unavailable");
      const user = await res.json() as User;
      if (user.role !== "FOUNDER" && user.role !== "ADMIN" && user.canAdmin !== true) { router.replace("/account"); return; }
      setAllowed(true);
    }).catch(() => setError("Berechtigung konnte nicht geprüft werden.")).finally(() => setChecking(false));
  },[router]);
  const change = (id:number,key:keyof Entry,value:string) => setRows(old=>old.map(r=>r.id===id ? {...r,[key]:value}:r));
  const exportCsv = () => {
    setError("");
    const valid = rows.filter(r=>r.name.trim() || r.set.trim() || r.number.trim() || r.price.trim());
    if (!valid.length) { setError("Bitte zuerst mindestens eine Karte eingeben."); return; }
    for (const r of valid) {
      if (!r.name.trim() || !r.set.trim() || !r.number.trim() || !Number.isFinite(euros(r.price)) || euros(r.price) <= 0 || !/^\d+$/.test(r.quantity) || Number(r.quantity)<1) {
        setError("Bitte Name, Set, Kartennummer, positiven Preis und eine Stückzahl ab 1 für jede Karte eintragen."); return;
      }
      if (r.image.trim() && !/^https:\/\//i.test(r.image.trim())) { setError("Bild-URLs müssen mit https:// beginnen."); return; }
    }
    const url = URL.createObjectURL(new Blob([makeCsv(valid)],{type:"text/csv;charset=utf-8"}));
    const a=document.createElement("a");a.href=url;a.download="cardyssey-einzelkarten-woocommerce.csv";a.click();
    URL.revokeObjectURL(url);
  };
  return <AppShell active="/admin">
    <section className="pageIntro"><div><span className="eyebrowText">Shop-Verwaltung</span><h1>Einzelkarten listen</h1><p>Karten selbst erfassen und als WooCommerce-CSV gesammelt importieren. Alle Produkte werden als <strong>Entwurf</strong> angelegt.</p></div></section>
    {!allowed ? <div className="statusPanel">{checking ? "Berechtigung wird geprüft …" : error || "Kein Zugriff."}</div> :
    <>
      <div className="statusPanel" style={{marginBottom:20}}>
        <strong>So geht’s:</strong> Karten eintragen → CSV herunterladen → in WordPress unter <strong>Produkte → Alle Produkte → Importieren</strong> hochladen → Vorschau prüfen → Import starten. Die Produkte bleiben bis zur Veröffentlichung Entwürfe.
        <p style={{marginBottom:0}}>Der Import benutzt WooCommerce-Standardfelder. Für Produktbilder optional eine direkte HTTPS-Bildadresse eintragen; Bildrechte prüfen. Bilder, Preise, Versand und Steuerklasse vor Veröffentlichung kontrollieren.</p>
      </div>
      {rows.map((r,index)=><section key={r.id} className="accountCard" style={{display:"block",marginBottom:16}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:12,marginBottom:18}}>
          <h2>Karte {index+1}</h2><button type="button" className="ghostButton" onClick={()=>setRows(old=>old.length===1?[blank(r.id)]:old.filter(x=>x.id!==r.id))}>Entfernen</button>
        </div>
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))",gap:12}}>
          {([["name","Kartenname"],["set","Set"],["number","Kartennummer"],["price","VK-Preis (€)"],["quantity","Stückzahl"],["image","Bild-URL (optional)"],["notes","Beschreibung (optional)"]] as const).map(([key,label])=><label key={key} style={{display:"grid",gap:5,fontWeight:700}}>{label}<input value={r[key]} onChange={e=>change(r.id,key,e.target.value)} type={key==="quantity"?"number":"text"} min={key==="quantity"?1:undefined} placeholder={key==="price"?"1,50":key==="number"?"025/198":""} style={{width:"100%",minHeight:44,padding:10,borderRadius:10,border:"1px solid var(--border)",background:"var(--navy-card)",color:"var(--text)"}}/></label>)}
          {([["language","Sprache",["Deutsch","Englisch","Japanisch","Koreanisch","Chinesisch (vereinfacht)","Chinesisch (traditionell)"]],["variant","Variante",["Normal","Holo","Reverse Holo","Full Art","Illustration Rare","Special Illustration Rare","Secret Rare","Promo","Sonstige"]],["condition","Zustand",["Near Mint","Excellent","Good","Light Played","Played","Poor"]]] as const).map(([key,label,values])=><label key={key} style={{display:"grid",gap:5,fontWeight:700}}>{label}<select value={r[key]} onChange={e=>change(r.id,key,e.target.value)} style={{width:"100%",minHeight:44,padding:10,borderRadius:10,border:"1px solid var(--border)",background:"var(--navy-card)",color:"var(--text)"}}>{values.map(v=><option key={v}>{v}</option>)}</select></label>)}
        </div>
      </section>)}
      {error && <div role="alert" className="statusPanel errorPanel" style={{marginBottom:16}}>{error}</div>}
      <div style={{display:"flex",flexWrap:"wrap",gap:12,marginBottom:30}}>
        <button className="ghostButton" type="button" onClick={()=>setRows(old=>[...old,blank(Math.max(...old.map(x=>x.id))+1)])}>+ Weitere Karte</button>
        <button className="primaryButton" type="button" onClick={exportCsv}>CSV für WooCommerce herunterladen</button>
        <Link href="/preview-shop" className="ghostButton" style={{display:"inline-flex",alignItems:"center"}}>Shop-Vorschau</Link>
      </div>
      <p className="muted">Hinweis: Eingaben werden nur in diesem Browserformular gehalten, nicht automatisch gespeichert. Vor dem Verlassen CSV herunterladen. Eine direkte Synchronisierung und Bearbeitung bestehender Shopartikel ist noch nicht eingerichtet.</p>
    </>}
  </AppShell>;
}
