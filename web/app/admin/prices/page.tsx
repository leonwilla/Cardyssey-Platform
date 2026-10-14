"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { AdminPriceCoverage } from "@/components/AdminPriceCoverage";
import type { User } from "@/lib/types";

type PriceCase = {
  cardId:string; languageCode:string; setName:string; cardName:string; cardNumber:string;
  variantId:string; variant:string; lastPriceEur?:number|null; source?:string|null;
  lastSuccessfulSync?:string|null; currentStatus:string; failureDetail?:string|null;
  nextAttemptAt?:string|null; identityMethod?:string|null;
};
type ResponseData = {
  counts:{total:number;stale:number;noPrice:number;providerError:number;noPublicPrice:number};
  items:PriceCase[];
};

type PriceReview = {
 languageCode:string;cardId:string;variantId:string;searchStatus:string;
 searchQuery?:string|null;searchSteps:string;candidates:string;
 failureReason?:string|null;checkedAt:string;
 referencePriceEur?:number|null;referenceSource?:string|null;referenceStatus?:string|null;referenceVerification?:string|null;ownerCount:number;ownedCopies:number;
};
function diagnosticJson(value:string):unknown[] {
 try { const parsed:unknown=JSON.parse(value);return Array.isArray(parsed)?parsed:[]; } catch{return [];}
}
const LANGUAGES=[["","Alle Sprachen"],["de","Deutsch"],["en","Englisch"],["ja","Japanisch"],["ko","Koreanisch"],["zh-tw","Chinesisch (trad.)"],["zh-cn","Chinesisch (vereinf.)"]];
const STATUSES=[["","Alle offenen"],["STALE","> 8 Tage"],["NO_PRICE","NO_PRICE"],["PROVIDER_ERROR","PROVIDER_ERROR"]];

function date(value?:string|null){if(!value)return "Noch nie";return new Intl.DateTimeFormat("de-DE",{dateStyle:"medium",timeStyle:"short"}).format(new Date(value));}
function euro(value?:number|null){return value==null?"—":new Intl.NumberFormat("de-DE",{style:"currency",currency:"EUR"}).format(value);}

export default function PriceMonitorPage(){
 const router=useRouter();
 const [user,setUser]=useState<User|null>(null);
 const [data,setData]=useState<ResponseData|null>(null);
 const [reviews,setReviews]=useState<PriceReview[]>([]);
 const [ownedOnly,setOwnedOnly]=useState(false);
 const [manualCase,setManualCase]=useState<PriceReview|null>(null);
 const [manualPrice,setManualPrice]=useState("");
 const [manualCondition,setManualCondition]=useState("NEAR_MINT");
 const [manualUrl,setManualUrl]=useState("");
 const [manualNote,setManualNote]=useState("");
 const [manualConfirmed,setManualConfirmed]=useState(false);
 const [manualSaving,setManualSaving]=useState(false);
 const [language,setLanguage]=useState("");
 const [status,setStatus]=useState("");
 const [loading,setLoading]=useState(true);
 const [message,setMessage]=useState<string|null>(null);

 useEffect(()=>{void initialize();},[]);
 useEffect(()=>{if(user)void load();},[language,status]);

 async function initialize(){
  try{
   const meResponse=await fetch("/api/auth/me",{cache:"no-store"});
   if(meResponse.status===401){router.replace("/login");return;}
   const me=await meResponse.json() as User;
   if(me.canAdmin!==true&&me.role!=="ADMIN"&&me.role!=="FOUNDER"){router.replace("/account");return;}
   setUser(me); await load();
  }catch{setMessage("Preis-Monitor konnte nicht geladen werden.");setLoading(false);}
 }
 async function load(){
  setLoading(true);setMessage(null);
  const params=new URLSearchParams();if(language)params.set("language",language);if(status)params.set("status",status);
  try{
   const response=await fetch(`/api/admin/price-monitor?${params.toString()}`,{cache:"no-store"});
   if(!response.ok)throw new Error();
   setData(await response.json() as ResponseData);
   const reviewResponse=await fetch(`/api/admin/price-review?${params.toString()}`,{cache:"no-store"});
   if(reviewResponse.ok)setReviews(await reviewResponse.json() as PriceReview[]);
  }catch{setMessage("Offene Preisfälle konnten nicht geladen werden.");}
  finally{setLoading(false);}
 }
 const copyText=useMemo(()=>data?.items.map((item,index)=>
  `${index+1}. [${item.currentStatus}] ${item.languageCode.toUpperCase()} | ${item.setName} | ${item.cardName} | #${item.cardNumber} | ${item.variant} | letzter Preis: ${euro(item.lastPriceEur)} | Quelle: ${item.source??"—"} | letzter erfolgreicher Sync: ${item.lastSuccessfulSync??"nie"} | Grund: ${item.failureDetail??"—"} | Identity: ${item.identityMethod??"keine"} | nächster Versuch: ${item.nextAttemptAt??"—"} | cardId=${item.cardId} | variantId=${item.variantId}`
 ).join("\n")??"",[data]);
 async function saveManual(){
  if(!manualCase||manualCase.ownerCount<1||!manualConfirmed)return;
  const price=Number(manualPrice.replace(",","."));
  if(!Number.isFinite(price)||price<=0){setMessage("Bitte einen gültigen Europreis eingeben.");return;}
  setManualSaving(true);setMessage(null);
  try{
   const response=await fetch("/api/admin/price-review/manual",{
    method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
     languageCode:manualCase.languageCode,cardId:manualCase.cardId,variantId:manualCase.variantId,
     priceEur:price,condition:manualCondition,sourceUrl:manualUrl,
     note:manualNote,exactPrintConfirmed:manualConfirmed
    })
   });
   if(!response.ok)throw new Error("Speichern abgelehnt. Karte nicht im Besitz, schon bepreist oder Angaben ungültig.");
   setManualCase(null);setManualPrice("");setManualUrl("");setManualNote("");setManualConfirmed(false);
   await load();setMessage("Manueller Variantenpreis mit Quellenbeleg gespeichert.");
  }catch(e){setMessage(e instanceof Error?e.message:"Preis konnte nicht gespeichert werden.");}
  finally{setManualSaving(false);}
 }

 async function copyList(){await navigator.clipboard.writeText(`Cardyssey offene Preisfälle (${data?.items.length??0})\nFilter: Sprache=${language||"alle"}, Status=${status||"alle"}\n\n${copyText}`);setMessage(`${data?.items.length??0} Preisfälle kopiert.`);}

 return <AppShell active="/admin/prices" user={user}>
  <section className="pageIntro"><div><span className="eyebrowText">Admin · Pricing</span><h1>Preis-Monitoring</h1><p>Nur offene Fälle: älter als 8 Tage, NO_PRICE oder PROVIDER_ERROR. Erfolgreiche Aktualisierungen verschwinden automatisch.</p></div></section>
  {message&&<div className="statusPanel">{message}</div>}
  {data&&<section className="statsGrid">
   <div className="statCard heroStat"><span>Offen gesamt</span><strong>{data.counts.total}</strong><small>ungefilterter Bestand</small></div>
   <div className="statCard"><span>&gt; 8 Tage</span><strong>{data.counts.stale}</strong><small>Preis-Sync veraltet</small></div>
   <div className="statCard"><span>NO_PRICE</span><strong>{data.counts.noPrice}</strong><small>weiter ohne Preis</small></div>
   <div className="statCard"><span>PROVIDER_ERROR</span><strong>{data.counts.providerError}</strong><small>Providerfehler</small></div>
   <div className="statCard"><span>Ohne öffentlichen Preis</span><strong>{data.counts.noPublicPrice}</strong><small>markiert · aktuell ignoriert</small></div>
  </section>}
  <section className="sectionBlock">
   <div className="sectionTitle"><div><span className="eyebrowText">Preis-Prüfung</span><h2>Unklare und erfolglose Suchläufe</h2></div><span className="chip mutedChip">{reviews.filter(r=>!ownedOnly||r.ownerCount>0).length} Fälle · {reviews.filter(r=>r.ownerCount>0).length} in Sammlungen</span></div>
   <p>Gespeicherte Suchbegriffe, geprüfte Schritte, Produktkandidaten und Fehlergründe. Fälle mit mittlerweile bestätigtem Preis werden ausgeblendet.</p>
   <div className="filterRow" style={{marginBottom:16}}>
    <label><input type="checkbox" checked={ownedOnly} onChange={e=>setOwnedOnly(e.target.checked)} /> Nur Karten mit Besitzern (manuelle Priorität)</label>
    <button className="primaryButton" type="button" disabled={!reviews.length} onClick={()=>void navigator.clipboard.writeText(reviews.filter(r=>!ownedOnly||r.ownerCount>0).map(r=>`[${r.searchStatus}] ${r.languageCode} ${r.cardId} ${r.variantId} | Suche: ${r.searchQuery??"—"} | Schritte: ${r.searchSteps} | Ursache: ${r.failureReason??"—"} | Besitzer: ${r.ownerCount} | Exemplare: ${r.ownedCopies} | Referenz: ${r.referencePriceEur??"—"} EUR (unbestätigt) | Kandidaten: ${r.candidates}`).join("\n"))}>Prüfliste kopieren</button>
   </div>
   {manualCase&&<form className="statusPanel" onSubmit={e=>{e.preventDefault();void saveManual();}} style={{display:"grid",gap:12,marginBottom:15}}>
    <strong>Manuellen Variantenpreis eintragen: {manualCase.languageCode.toUpperCase()} · {manualCase.cardId} · {manualCase.variantId}</strong>
    <p>Nur für diese genaue Karte und Druckvariante. Der Beleg wird dauerhaft protokolliert; die Eingabe wird zum TCG-Marktwert und zählt dann zur Sammlung. Nicht als allgemeine Schätzung verwenden.</p>
    <div className="filterRow">
     <label>Preis in € für den gewählten Zustand
      <input type="text" inputMode="decimal" required value={manualPrice} onChange={e=>setManualPrice(e.target.value)} placeholder="z. B. 14,99" />
     </label>
     <label>Zustand
      <select value={manualCondition} onChange={e=>setManualCondition(e.target.value)}>
       {["MINT","NEAR_MINT","EXCELLENT","GOOD","PLAYED"].map(c=><option key={c} value={c}>{c}</option>)}
      </select>
     </label>
     <label>Quellenlink (https)
      <input type="url" required pattern="https://.*" value={manualUrl} onChange={e=>setManualUrl(e.target.value)} placeholder="https://www.cardmarket.com/..." />
     </label>
    </div>
    <label>Bemerkung (optional)
     <input value={manualNote} onChange={e=>setManualNote(e.target.value)} placeholder="Druck, Stempel, Edition und Quelle" maxLength={500} />
    </label>
    <label><input type="checkbox" checked={manualConfirmed} onChange={e=>setManualConfirmed(e.target.checked)} required /> Ich habe Sprache, Kartennummer, Set, Stempel, Druckvariante und Zustand anhand der Quelle geprüft.</label>
    <div className="filterRow">
     <button className="primaryButton" type="submit" disabled={manualSaving||!manualConfirmed||!manualPrice||!manualUrl}>{manualSaving?"Speichert …":"Preis verbindlich speichern"}</button>
     <button className="ghostButton" type="button" onClick={()=>setManualCase(null)}>Abbrechen</button>
    </div>
   </form>}
   <div style={{maxHeight:"48vh",overflow:"auto"}}>
    <table style={{width:"100%",minWidth:1000,borderCollapse:"collapse"}}>
     <thead><tr>{["Sprache","Karte","Suchbegriff","Ergebnis","Besitzer","Referenzpreis (unbestätigt)","Problem / Schritte", "Kandidaten","Geprüft","Manuell"].map(v=><th key={v} style={{textAlign:"left",padding:9}}>{v}</th>)}</tr></thead>
     <tbody>{reviews.filter(r=>!ownedOnly||r.ownerCount>0).map(r=><tr key={`${r.languageCode}:${r.cardId}:${r.variantId}`}>
      <td style={{padding:9}}>{r.languageCode.toUpperCase()}</td>
      <td style={{padding:9}}>{r.cardId}<small style={{display:"block"}}>{r.variantId}</small></td>
      <td style={{padding:9}}>{r.searchQuery??"—"}</td>
      <td style={{padding:9}}>{r.searchStatus}</td>
      <td style={{padding:9}}>{r.ownerCount} Nutzer<small style={{display:"block"}}>{r.ownedCopies} Exemplare</small></td>
      <td style={{padding:9}}>{r.referencePriceEur!=null?<><strong>{euro(r.referencePriceEur)}</strong><small style={{display:"block"}}>EN · Druckvariante ungeprüft</small><details><summary>Prüfgründe</summary><small style={{whiteSpace:"pre-wrap"}}>{diagnosticJson(r.referenceVerification??"[]").join(", ")}</small></details></>:"—"}</td>
      <td style={{padding:9,maxWidth:300}}>{r.failureReason??"—"}<details><summary>Suchweg</summary><pre style={{whiteSpace:"pre-wrap"}}>{diagnosticJson(r.searchSteps).join(" → ")}</pre></details></td>
      <td style={{padding:9}}><details><summary>{diagnosticJson(r.candidates).length} Treffer</summary><pre style={{whiteSpace:"pre-wrap"}}>{JSON.stringify(diagnosticJson(r.candidates),null,2)}</pre></details></td>
      <td style={{padding:9}}>{date(r.checkedAt)}</td>
      <td style={{padding:9}}>{r.ownerCount>0?<button className="ghostButton" type="button" onClick={()=>{setManualCase(r);setManualConfirmed(false);setManualUrl("");setManualPrice("");}}>Preis prüfen / eintragen</button>:"Nur bei Sammlungskarten"}</td>
     </tr>)}</tbody>
    </table>
   </div>
  </section>
  {user && <AdminPriceCoverage />}
  <section className="sectionBlock">
   <div className="sectionTitle"><div><span className="eyebrowText">Arbeitsliste</span><h2>Offene Kartenvarianten</h2></div><span className="chip mutedChip">{data?.items.length??0} angezeigt</span></div>
   <div className="filterRow" style={{marginBottom:16}}>
    <select value={language} onChange={e=>setLanguage(e.target.value)}>{LANGUAGES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
    <select value={status} onChange={e=>setStatus(e.target.value)}>{STATUSES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
    <button className="ghostButton" type="button" onClick={()=>void load()} disabled={loading}>{loading?"Lädt …":"Aktualisieren"}</button>
    <button className="primaryButton" type="button" onClick={()=>void copyList()} disabled={!data?.items.length}>Liste kopieren</button>
   </div>
   {loading?<div className="statusPanel">Preisfälle werden geladen …</div>:
    <div style={{overflowX:"auto",maxHeight:"68vh",overflowY:"auto"}}>
     <table style={{width:"100%",borderCollapse:"collapse",minWidth:1600}}>
      <thead style={{position:"sticky",top:0,background:"var(--panel)",zIndex:1}}><tr>{["Sprache","Set","Name","Nr.","Variante","Letzter Preis","Quelle","Letzter Erfolg","Identity","Grund","Nächster Versuch","Status"].map(x=><th key={x} style={{textAlign:"left",padding:"10px",borderBottom:"1px solid var(--border)"}}>{x}</th>)}</tr></thead>
      <tbody>{data?.items.map(item=><tr key={`${item.languageCode}:${item.cardId}:${item.variantId}`}>
       <td style={{padding:10}}>{item.languageCode.toUpperCase()}</td><td style={{padding:10}}>{item.setName}</td><td style={{padding:10}}>{item.cardName}</td><td style={{padding:10}}>{item.cardNumber}</td><td style={{padding:10}}>{item.variant}</td><td style={{padding:10}}>{euro(item.lastPriceEur)}</td><td style={{padding:10}}>{item.source??"—"}</td><td style={{padding:10}}>{date(item.lastSuccessfulSync)}</td><td style={{padding:10}}>{item.identityMethod??"—"}</td><td style={{padding:10,maxWidth:320,whiteSpace:"normal"}}>{item.failureDetail??"—"}</td><td style={{padding:10}}>{item.nextAttemptAt?date(item.nextAttemptAt):"—"}</td><td style={{padding:10}}><span className="chip mutedChip">{item.currentStatus}</span></td>
      </tr>)}</tbody>
     </table>
    </div>}
  </section>
 </AppShell>;
}
