"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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
 referencePriceEur?:number|null;referenceSource?:string|null;referenceStatus?:string|null;referenceVerification?:string|null;ownerCount:number;ownedCopies:number;cardName?:string|null;cardNumber?:string|null;setId?:string|null;variantDetails?:string|null;setName?:string|null;printedNumber?:string|null;
};
function diagnosticJson(value:string):unknown[] {
 try { const parsed:unknown=JSON.parse(value);return Array.isArray(parsed)?parsed:[]; } catch{return [];}
}
function variantLabel(details?:string|null){
 try {
  const v=JSON.parse(details??"null") as Record<string,unknown>|null;
  if(!v||typeof v!=="object")return "Druckvariante im Katalog nicht gefunden";
  const parts=[v.type,v.subtype,v.foil,
   typeof v.size==="string"&&v.size.toLowerCase()!=="standard"?v.size:null,
   ...(Array.isArray(v.stamps)?v.stamps:[])];
  return parts.filter((x):x is string=>typeof x==="string"&&x.length>0).join(" · ")||"Unbekannte Ausgabe";
 }catch{return "Druckvariante unbekannt";}
}
const LANGUAGES=[["","Alle Sprachen"],["de","Deutsch"],["en","Englisch"],["ja","Japanisch"],["ko","Koreanisch"],["zh-tw","Chinesisch (trad.)"],["zh-cn","Chinesisch (vereinf.)"]];
const STATUSES=[["","Alle offenen"],["STALE","> 8 Tage"],["NO_PRICE","NO_PRICE"],["NO_PUBLIC_PRICE","Kein öffentlicher Preis"],["PROVIDER_ERROR","PROVIDER_ERROR"]];

function reviewIdentity(r:PriceReview){
 const number=r.printedNumber??r.cardNumber??"?";
 const set=r.setName&&r.setName!==r.setId?r.setName+" ("+(r.setId??"?")+")":r.setId??"?";
 return (r.cardName??r.cardId)+" · "+number+" · "+set+" · "+r.languageCode.toUpperCase()+" · "+variantLabel(r.variantDetails);
}
function reviewSearch(r:PriceReview){
 return "Pokémon "+reviewIdentity(r).replaceAll(" · "," ");
}
function date(value?:string|null){if(!value)return "Noch nie";return new Intl.DateTimeFormat("de-DE",{dateStyle:"medium",timeStyle:"short"}).format(new Date(value));}
function euro(value?:number|null){return value==null?"—":new Intl.NumberFormat("de-DE",{style:"currency",currency:"EUR"}).format(value);}

export default function PriceMonitorPage(){
 const router=useRouter();
 const [user,setUser]=useState<User|null>(null);
 const [data,setData]=useState<ResponseData|null>(null);
 const [reviews,setReviews]=useState<PriceReview[]>([]);
 const [ownedOnly,setOwnedOnly]=useState(false);
 const [cardmarketOnly,setCardmarketOnly]=useState(false);
 const [activePanel,setActivePanel]=useState("review");
 const [cardSearch,setCardSearch]=useState("");
 const [detailsId,setDetailsId]=useState<string|null>(null);
 const [manualCase,setManualCase]=useState<PriceReview|null>(null);
 const [manualPrice,setManualPrice]=useState("");
 const [manualCondition,setManualCondition]=useState("NEAR_MINT");
 const [manualUrl,setManualUrl]=useState("");
 const [sourcePreview,setSourcePreview]=useState<{title?:string|null;suggestedPrice?:number|null;currency?:string|null;status:string;evidence:string}|null>(null);
 const [sourceLoading,setSourceLoading]=useState(false);

 const [manualNote,setManualNote]=useState("");
 const [manualConfirmed,setManualConfirmed]=useState(false);
 const [manualSaving,setManualSaving]=useState(false);
 const [language,setLanguage]=useState("");
 const [status,setStatus]=useState("");
 const [loading,setLoading]=useState(true);
 const [message,setMessage]=useState<string|null>(null);




 const initialize = useCallback(async () => {
  try{
   const meResponse=await fetch("/api/auth/me",{cache:"no-store"});
   if(meResponse.status===401){router.replace("/login");return;}
   const me=await meResponse.json() as User;
   if(me.canAdmin!==true&&me.role!=="ADMIN"&&me.role!=="FOUNDER"){router.replace("/account");return;}
   setUser(me);
  }catch{setMessage("Preis-Monitor konnte nicht geladen werden.");setLoading(false);}
 }, [router]);
 const load = useCallback(async () => {
  setLoading(true);setMessage(null);
  const params=new URLSearchParams();if(language)params.set("language",language);if(status)params.set("status",status);
  const responses=await Promise.allSettled([
   fetch("/api/admin/price-review?"+params.toString(),{cache:"no-store"}),
   fetch("/api/admin/price-monitor?"+params.toString(),{cache:"no-store"})
  ]);
  const review=responses[0];const monitor=responses[1];
  if(review.status==="fulfilled"&&review.value.ok)setReviews(await review.value.json() as PriceReview[]);
  else {setReviews([]);setMessage("Preisprüfliste derzeit nicht erreichbar. Bitte erneut aktualisieren.");}
  if(monitor.status==="fulfilled"&&monitor.value.ok)setData(await monitor.value.json() as ResponseData);
  else {setData(null);setMessage("Die Preis-Monitoring-Daten konnten nicht geladen werden. Das bedeutet nicht, dass keine offenen Karten vorhanden sind. Bitte erneut aktualisieren.");}
  setLoading(false);
 }, [language, status]);
 useEffect(()=>{void Promise.resolve().then(initialize);},[initialize]);
 useEffect(()=>{if(user)void Promise.resolve().then(load);},[user,load]);
 const copyText=useMemo(()=>data?.items.map((item,index)=>
  `${index+1}. [${item.currentStatus}] ${item.languageCode.toUpperCase()} | ${item.setName} | ${item.cardName} | #${item.cardNumber} | ${item.variant} | letzter Preis: ${euro(item.lastPriceEur)} | Quelle: ${item.source??"—"} | letzter erfolgreicher Sync: ${item.lastSuccessfulSync??"nie"} | Grund: ${item.failureDetail??"—"} | Identity: ${item.identityMethod??"keine"} | nächster Versuch: ${item.nextAttemptAt??"—"} | cardId=${item.cardId} | variantId=${item.variantId}`
 ).join("\n")??"",[data]);
 async function evaluateSource(){
  if(!manualUrl.trim())return;
  setSourceLoading(true);setSourcePreview(null);
  try{
   const response=await fetch("/api/admin/price-review/link-preview",{
    method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:manualUrl})
   });
   const result=await response.json();
   if(!response.ok)throw new Error("Nur öffentliche HTTPS-Links von Cardmarket, TCGplayer und PriceCharting sind erlaubt.");
   setSourcePreview(result);
  }catch(e){setMessage(e instanceof Error?e.message:"Link konnte nicht geprüft werden.");}
  finally{setSourceLoading(false);}
 }

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

 const filteredReviews=reviews.filter(r=>(!ownedOnly||r.ownerCount>0)&&
  (!cardmarketOnly||r.searchStatus==="CARDMARKET_PRINT_REVIEW")&&
  [r.cardName,r.cardId,r.setId,r.setName,r.cardNumber,r.printedNumber,r.languageCode,variantLabel(r.variantDetails),r.searchQuery].join(" ").toLowerCase().includes(cardSearch.toLowerCase()));
 return <AppShell active="/admin/prices" user={user}>
  <section className="pageIntro"><div><span className="eyebrowText">Admin · Pricing</span><h1>Preise verwalten</h1><p>Prüfe einzelne Karten, finde Kataloglücken und kontrolliere die Synchronisierung – alles getrennt und übersichtlich.</p></div></section>
  {message&&<div className="statusPanel">{message}</div>}
  <div className="filterRow" style={{marginBottom:22,gap:12}}>
   <button type="button" className={activePanel==="review"?"primaryButton":"ghostButton"} onClick={()=>setActivePanel("review")}>Karten prüfen</button>
   <button type="button" className={activePanel==="coverage"?"primaryButton":"ghostButton"} onClick={()=>setActivePanel("coverage")}>Alle Kataloglücken</button>
   <button type="button" className={activePanel==="monitor"?"primaryButton":"ghostButton"} onClick={()=>setActivePanel("monitor")}>Synchronisierung</button>
  </div>
  {activePanel==="monitor"&&data&&<section className="statsGrid">
   <div className="statCard heroStat"><span>Offen gesamt</span><strong>{data.counts.total}</strong><small>ungefilterter Bestand</small></div>
   <div className="statCard"><span>&gt; 8 Tage</span><strong>{data.counts.stale}</strong><small>Preis-Sync veraltet</small></div>
   <div className="statCard"><span>NO_PRICE</span><strong>{data.counts.noPrice}</strong><small>weiter ohne Preis</small></div>
   <div className="statCard"><span>PROVIDER_ERROR</span><strong>{data.counts.providerError}</strong><small>Providerfehler</small></div>
   <div className="statCard"><span>Ohne öffentlichen Preis</span><strong>{data.counts.noPublicPrice}</strong><small>markiert · aktuell ignoriert</small></div>
  </section>}
  {activePanel==="review"&&<section className="sectionBlock">
   <div className="sectionTitle"><div><span className="eyebrowText">Preis-Prüfung</span><h2>Unklare und erfolglose Suchläufe</h2></div><span className="chip mutedChip">{filteredReviews.length} Fälle · {reviews.filter(r=>r.ownerCount>0).length} exakt gehaltene Varianten</span></div>
   <p>Gespeicherte Suchbegriffe, geprüfte Schritte, Produktkandidaten und Fehlergründe. Fälle mit mittlerweile bestätigtem Preis werden ausgeblendet.</p>
   <div className="filterRow" style={{marginBottom:16}}>
    <label style={{display:"flex",alignItems:"center",gap:6}}><input type="checkbox" checked={cardmarketOnly} onChange={e=>setCardmarketOnly(e.target.checked)}/> Nur Cardmarket-Druckvarianten (23)</label>
    <input aria-label="Karten suchen" placeholder="Kartenname, Set, Sprache suchen …" value={cardSearch} onChange={e=>setCardSearch(e.target.value)}/>
    <select aria-label="Sprache auswählen" value={language} onChange={e=>setLanguage(e.target.value)}>{LANGUAGES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
    <button className="ghostButton" type="button" onClick={()=>void load()} disabled={loading}>Aktualisieren</button>
    <label><input type="checkbox" checked={ownedOnly} onChange={e=>setOwnedOnly(e.target.checked)} /> Nur exakt gehaltene Druckvarianten</label>
    <button className="primaryButton" type="button" disabled={!reviews.length} onClick={()=>void navigator.clipboard.writeText(reviews.filter(r=>!ownedOnly||r.ownerCount>0).map(r=>`[${r.searchStatus}] ${reviewIdentity(r)} | cardId=${r.cardId} variantId=${r.variantId} | Suche: ${r.searchQuery??"—"} | Schritte: ${r.searchSteps} | Ursache: ${r.failureReason??"—"} | Besitzer: ${r.ownerCount} | Exemplare: ${r.ownedCopies} | Referenz: ${r.referencePriceEur??"—"} EUR (unbestätigt) | Kandidaten: ${r.candidates}`).join("\n"))}>Prüfliste kopieren</button>
   </div>
   {manualCase&&<form className="statusPanel" onSubmit={e=>{e.preventDefault();void saveManual();}} style={{display:"grid",gap:12,marginBottom:15}}>
    <strong>Manuellen Variantenpreis eintragen: {reviewIdentity(manualCase)}</strong>
    <p><strong>Genaue Druckvariante:</strong> {variantLabel(manualCase.variantDetails)} · ID {manualCase.variantId}</p>
    <p>Link einfügen und automatisch auswerten. Die Preisübernahme ist nur möglich, wenn jemand diese exakte Druckvariante besitzt und die Angaben bestätigt wurden.</p>
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
      <input type="url" required pattern="https://.*" value={manualUrl} onChange={e=>{setManualUrl(e.target.value);setSourcePreview(null);}} placeholder="https://www.cardmarket.com/..." />
     </label>
     <button type="button" className="ghostButton" disabled={!manualUrl||sourceLoading} onClick={()=>void evaluateSource()}>{sourceLoading?"Prüfe Quelle …":"Link auswerten"}</button>
    </div>
    {sourcePreview&&<div className="statusPanel" role="status">
     <strong>{sourcePreview.title??"Gefundene Quelle"}</strong>
     <p>{sourcePreview.suggestedPrice!=null?"Preismetadaten: "+sourcePreview.suggestedPrice+" "+(sourcePreview.currency??"Währung unbekannt"):"Kein maschinenlesbarer Preis gefunden."}</p>
     <small>{sourcePreview.evidence}</small>
     <p>Der Vorschlag wird nicht automatisch übernommen. Bitte prüfen, ob das Angebot exakt zur ausgewählten Karte passt.</p>
    </div>}
    {manualCase.ownerCount===0&&<p>Aktuell besitzt niemand diese exakte Variante. Der Link kann geprüft werden, aber ein Marktpreis wird noch nicht übernommen.</p>}
    <label>Bemerkung (optional)
     <input value={manualNote} onChange={e=>setManualNote(e.target.value)} placeholder="Druck, Stempel, Edition und Quelle" maxLength={500} />
    </label>
    <label><input type="checkbox" checked={manualConfirmed} onChange={e=>setManualConfirmed(e.target.checked)} required /> Ich habe Sprache, Kartennummer, Set, Stempel, Druckvariante und Zustand anhand der Quelle geprüft.</label>
    <div className="filterRow">
     <button className="primaryButton" type="submit" disabled={manualCase.ownerCount===0||manualSaving||!manualConfirmed||!manualPrice||!manualUrl}>{manualSaving?"Speichert …":"Preis verbindlich speichern"}</button>
     <button className="ghostButton" type="button" onClick={()=>setManualCase(null)}>Abbrechen</button>
    </div>
   </form>}
   {loading&&!reviews.length&&<p>Preisprüfungen werden geladen …</p>}
   {!loading&&!filteredReviews.length&&<p className="statusPanel">Keine Karten gefunden. Prüfe Suche, Sprache und Besitzfilter.</p>}
   <div style={{display:"grid",gap:12}}>
    {filteredReviews.map(r=>{
     const key=r.languageCode+":"+r.cardId+":"+r.variantId;
     return <article className="statusPanel" key={key} style={{padding:18}}>
      <div style={{display:"flex",gap:16,justifyContent:"space-between",alignItems:"center",flexWrap:"wrap"}}>
       <div style={{flex:"1 1 230px"}}>
        <strong style={{fontSize:20}}>{r.cardName??r.cardId}</strong>
        <div style={{fontSize:16,fontWeight:700,marginTop:5}}>Nr. {r.printedNumber??r.cardNumber??"?"} · {r.setName??r.setId} ({r.setId}) · {r.languageCode.toUpperCase()}</div>
        <div style={{marginTop:4}}>Druckvariante: {variantLabel(r.variantDetails)}</div>
        <small>{r.ownerCount} Besitzer · {r.ownedCopies} Exemplare</small>
       </div>
       <div style={{flex:"0 1 200px"}}>
        <strong>{euro(r.referencePriceEur)}</strong>
        <small style={{display:"block"}}>{r.referenceStatus==="CROSS_LANGUAGE_REFERENCE"?"Englischer Vergleichswert":"Ungeprüfter Referenzwert"}</small>
       </div>
       <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
        <a className="ghostButton" href={"https://www.google.com/search?q="+encodeURIComponent(reviewSearch(r))} target="_blank" rel="noopener noreferrer">Websuche ↗</a>
        <button className="ghostButton" type="button" onClick={()=>setDetailsId(detailsId===key?null:key)}>Details</button>
        <button className="primaryButton" type="button" onClick={()=>{setManualCase(r);setSourcePreview(null);setManualUrl("");setManualPrice("");setManualConfirmed(false);}}>Quelle eintragen</button>
       </div>
      </div>
      {detailsId===key&&<div style={{marginTop:12}}>
       <p><strong>Problem:</strong> {r.failureReason??r.searchStatus}</p>
       <details><summary>Suchhistorie und Anbieter</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{JSON.stringify({steps:diagnosticJson(r.searchSteps),candidates:diagnosticJson(r.candidates),identity:diagnosticJson(r.referenceVerification??"[]")},null,2)}</pre></details>
       <small>Varianten-ID: {r.variantId}</small>
      </div>}
     </article>;
    })}
   </div>
  </section>}
  {activePanel==="coverage"&&user&&<AdminPriceCoverage />}
  {activePanel==="monitor"&&<section className="sectionBlock">
   <div className="sectionTitle"><div><span className="eyebrowText">Arbeitsliste</span><h2>Offene Kartenvarianten</h2></div><span className="chip mutedChip">{data?data.items.length+" angezeigt":"Keine Daten"}</span></div>
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
  </section>}
 </AppShell>;
}
