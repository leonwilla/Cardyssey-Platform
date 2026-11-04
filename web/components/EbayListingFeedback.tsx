'use client';
import {useState} from 'react';
const options=[
 ['WRONG_CARD','Falsche Karte'],
 ['VALID_SINGLE_SALE','Echter Einzelverkauf dieser Karte'],
 ['MULTI_SELECTION','Mehrfachauswahl-Angebot'],
 ['WRONG_VARIANT','Falsche Druckvariante'],
 ['PAID_PRICE_UNKNOWN','Verkaufspreis nicht nachweisbar'],
 ['OTHER','Anderer Fehler']
] as const;
export function EbayListingFeedback({cardId,itemId,title,initialFeedback}:{cardId:string;itemId:string;title:string;initialFeedback?:{decision:string;note:string}|null}){
 const [open,setOpen]=useState(false);
 const [decision,setDecision]=useState<string>(initialFeedback?.decision??'OTHER');
 const [note,setNote]=useState(initialFeedback?.note??'');
 const [saving,setSaving]=useState(false);
 const [message,setMessage]=useState(initialFeedback?'Bereits als Prüfbeispiel gespeichert':'');
 if(!/^[0-9]{9,15}$/.test(itemId))return null;
 async function save(){setSaving(true);setMessage('');try{
  const r=await fetch('/api/admin/price-listing-feedback',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({cardId,itemId,decision,note,title})});
  if(!r.ok)throw Error('Rückmeldung konnte nicht gespeichert werden.');
  setOpen(false);setMessage('Beispiel gespeichert · wird für Regelprüfung ausgewertet');
 }catch(e){setMessage(e instanceof Error?e.message:'Speichern fehlgeschlagen')}finally{setSaving(false)}}
 return <div style={{fontSize:12,marginTop:5}}>
  <button type="button" className="ghostButton" onClick={()=>setOpen(!open)}>{open?'Abbrechen':'Zuordnung korrigieren'}</button>
  {open&&<div style={{display:'grid',gap:6,padding:10,marginTop:6,border:'1px solid var(--border)',borderRadius:10}}>
   <label>Was ist bei diesem Angebot falsch oder richtig?
    <select style={{display:'block',width:'100%',marginTop:4}} value={decision} onChange={e=>setDecision(e.target.value)}>
     {options.map(([key,label])=><option key={key} value={key}>{label}</option>)}
    </select>
   </label>
   <textarea rows={2} maxLength={1000} aria-label="Erläuterung zum eBay-Angebot" placeholder="Was sollte unser Collector hier anders machen?" value={note} onChange={e=>setNote(e.target.value)}/>
   <div><button type="button" className="primaryButton" disabled={saving} onClick={()=>void save()}>{saving?'Speichere …':'Beispiel speichern'}</button></div>
   <small>Diese Rückmeldung ändert keine gespeicherten Preise. Wir nutzen sie zur Verbesserung und zum Testen der Erkennungsregeln.</small>
  </div>}
  {message&&<small aria-live="polite">{message}</small>}
 </div>
}
