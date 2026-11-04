'use client';
import {useEffect,useState} from 'react';

type Review={status:string;refreshDays:number;showOfferReferences:boolean;note:string};
type Reference={title:string;url:string;price:number|null;itemId?:string;purchaseHistoryStatus?:string|null;purchaseRowsCount?:number;purchaseRows?:{variant:string;displayedPrice:string;quantity:string;purchasedAt:string}[];seenAt?:string};
const defaults:Review={status:'AUTO',refreshDays:7,showOfferReferences:true,note:''};
const euros=(v:number|null)=>v==null?'Preis unbekannt':new Intl.NumberFormat('de-DE',{style:'currency',currency:'EUR'}).format(v);
export function EbayPriceReviewPanel({cardId,initial,offers}:{cardId:string;initial?:Review;offers?:Reference[]}){
 const [review,setReview]=useState<Review>(initial??defaults);
 const [saved,setSaved]=useState('');const [saving,setSaving]=useState(false);
 useEffect(()=>{setReview(initial??defaults);setSaved('')},[cardId,initial?.status,initial?.refreshDays,initial?.showOfferReferences,initial?.note]);
 async function save(){setSaving(true);setSaved('');try{
  const r=await fetch('/api/admin/price-review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cardId,...review})});
  if(!r.ok)throw new Error('Speichern fehlgeschlagen');setSaved('Gespeichert · beeinflusst den nächsten automatischen Scan');
 }catch(e){setSaved(e instanceof Error?e.message:'Fehler beim Speichern')}finally{setSaving(false)}}
 return <div style={{marginTop:16,padding:16,border:'1px solid var(--border)',borderRadius:12,display:'grid',gap:12}}>
  <strong>Manuelle Einordnung und Wiedervorlage</strong>
  <p style={{fontSize:13,margin:0}}>Diese Einordnung ändert keine gespeicherten Verkäufe oder Kartenpreise. Karten bleiben im Monitoring sichtbar, bis wir die Preisqualität geprüft haben.</p>
  <label style={{display:'grid',gap:4,fontSize:13}}>Prüfstatus
   <select value={review.status} onChange={e=>setReview(v=>({...v,status:e.target.value}))}>
    <option value="AUTO">Automatisch prüfen</option>
    <option value="NO_VERIFIED_SALE">Kein bestätigter Verkauf gefunden</option>
    <option value="OFFER_REVIEW">Auswahlangebot / Referenz manuell prüfen</option>
   </select>
  </label>
  <label style={{display:'grid',gap:4,fontSize:13}}>Nächste Suche frühestens nach
   <select value={review.refreshDays} onChange={e=>setReview(v=>({...v,refreshDays:Number(e.target.value)}))}>
    <option value={7}>7 Tagen</option><option value={14}>14 Tagen</option><option value={30}>30 Tagen</option>
   </select>
  </label>
  <label style={{fontSize:13,display:'flex',alignItems:'center',gap:8}}>
   <input type="checkbox" checked={review.showOfferReferences} onChange={e=>setReview(v=>({...v,showOfferReferences:e.target.checked}))}/>
   Unbestätigte Auswahlangebote im Monitoring anzeigen
  </label>
  <label style={{display:'grid',gap:4,fontSize:13}}>Notiz (optional)
   <textarea maxLength={500} rows={2} value={review.note} onChange={e=>setReview(v=>({...v,note:e.target.value}))} placeholder="Zum Beispiel: Tannza bisher nur in Auswahlangeboten"/>
  </label>
  <div style={{display:'flex',alignItems:'center',gap:12,flexWrap:'wrap'}}><button type="button" className="primaryButton" disabled={saving} onClick={()=>void save()}>{saving?'Speichert …':'Einordnung speichern'}</button>{saved&&<small aria-live="polite">{saved}</small>}</div>
  {review.showOfferReferences&&<div style={{borderTop:'1px solid var(--border)',paddingTop:12}}><strong>Mögliche Auswahlangebote ({offers?.length??0})</strong>
   <p style={{fontSize:12}}>Der Gesamtverkaufszähler belegt keinen Verkauf dieser Karte. Nur eine Transaktion mit eindeutigem Kartendruck, Datum und bezahltem Preis wird als Kartenverkauf in den Median übernommen. Käuferdaten werden nicht gespeichert.</p>
   {(offers??[]).length?<div style={{display:'grid',gap:10}}>{offers?.map((o,i)=><div key={`${o.url}-${i}`} style={{border:'1px solid var(--border)',borderRadius:10,padding:10,display:'grid',gap:6}}>
    <a href={o.url} target="_blank" rel="noopener noreferrer" style={{fontSize:13}}>{o.title} · Angebotspreis: {euros(o.price)} (keine Verkaufspreis-Bestätigung)</a>
    <small style={{fontWeight:700}}>{o.purchaseHistoryStatus==='VERIFIED_ROWS'?'Kaufübersicht geprüft: öffentlich sichtbare Transaktionen gefunden':o.purchaseHistoryStatus==='NO_VISIBLE_PRICE'?'Kaufübersicht geprüft: öffentlich sichtbare Käufe ohne ausgewiesenen Preis':o.purchaseHistoryStatus==='NO_PURCHASE_ROWS'?'Keine Transaktionen sichtbar':o.purchaseHistoryStatus==='UNSAFE_LAYOUT'?'Unbekanntes eBay-Layout – manuell prüfen':o.purchaseHistoryStatus==='BLOCKED'||o.purchaseHistoryStatus==='LOGIN_REQUIRED'?'Kaufübersicht nicht zugänglich':o.purchaseHistoryStatus==='UNAVAILABLE'?'eBay-Kaufübersicht nicht erreichbar':'Kaufübersicht noch nicht geprüft'} {o.purchaseRowsCount?`· ${o.purchaseRowsCount} Transaktionen`:''}</small>
    {(o.purchaseRows??[]).length>0&&<div style={{display:'grid',gap:4}}>{o.purchaseRows?.map((tx,j)=><small key={j} style={{display:'block'}}>{tx.variant} · {tx.displayedPrice} · {tx.quantity}× · {tx.purchasedAt}</small>)}</div>}
    {o.itemId&&<a href={`https://www.ebay.de/bin/purchaseHistory?item=${encodeURIComponent(o.itemId)}`} target="_blank" rel="noopener noreferrer" style={{fontSize:12}}>Kaufübersicht bei eBay öffnen und kontrollieren ↗</a>}
   </div>)}</div>:<small>Für diese Karte wurden noch keine möglichen Auswahlangebote separat erfasst. Ältere Suchprotokolle werden schrittweise nachgetragen.</small>}
  </div>}
 </div>;
}
