'use client';
import {useState} from 'react';
export type Entry={language:string;card_id:string;variant_id:string;set_id:string;card_name:string;
 printed_number:string;print_type:string;foil:string;subtype:string;stamps:string;
 candidate_ids:string[];matched_set_ids:string[];product_names:string;
 provider_expansion_id:string;classification:string;status:string;
 selected_product_id:string|null;reviewer_note:string|null;
 card_image_url?:string|null;
 diagnosis?:{kind:string;reason:string;action:string;proofAvailable:boolean;sameMetacard:boolean;candidates:{id:string;name:string;expansionId:string;metacardId:string;addedAt:string}[]};
 reference_values?:Record<string,{avg30:number|null;avg30_holo:number|null;trend:number|null;trend_holo:number|null}>;};
const buttonStyle={padding:'8px 12px'};
export function CardReview({entry,onSaved}:{entry:Entry;onSaved:()=>void}){
 const [pid,setPid]=useState(entry.matched_set_ids.length===1?entry.matched_set_ids[0]:'');
 const [note,setNote]=useState('');
 const [confirmed,setConfirmed]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const names=entry.product_names.split(' | ');
 const detail=entry.diagnosis;
 const candidate=(id:string)=>detail?.candidates.find(c=>c.id===id);
 const multipleSimilar=detail?.kind==='CATALOG_DUPLICATE'&&detail.sameMetacard;
 const searchLink=(id:string)=>'https://www.cardmarket.com/'+entry.language+'/Pokemon/Products/Search?searchString='+encodeURIComponent((candidate(id)?.name||entry.card_name||'')+' '+entry.printed_number);
 const reference=pid?entry.reference_values?.[pid]:undefined;
 const euro=(v:number|null|undefined)=>v==null?'–':new Intl.NumberFormat('de-DE',{style:'currency',currency:'EUR'}).format(v);
 async function save(status:'CONFIRMED_PRINT'|'NO_MATCH'|'DEFERRED'){
  setBusy(true);setError('');
  try{
   const r=await fetch('/api/admin/cardmarket-print-review',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({
     language:entry.language,cardId:entry.card_id,variantId:entry.variant_id,
     status,productId:status==='CONFIRMED_PRINT'?pid:'',
     exactPrintConfirmed:status==='CONFIRMED_PRINT'&&confirmed,note
    })});
   const data=await r.json();
   if(!r.ok)throw Error(data.error||'Speichern fehlgeschlagen');
   if(status==='CONFIRMED_PRINT'&&data.sourceRoutingUpdated===false){
    setError('Bestätigung gespeichert. Eine bereits verifizierte andere Preisquelle wurde nicht überschrieben.');
   }
   onSaved();
  }catch(e){setError(e instanceof Error?e.message:'Fehler')}
  finally{setBusy(false)}
 }
 return <article className="statusPanel" style={{padding:16,display:'grid',gap:10}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:12,flexWrap:'wrap'}}>
   <div>{entry.card_image_url?.startsWith('https://')&&<img src={entry.card_image_url}
    alt={'Pokémon-Karte '+(entry.card_name||entry.card_id)}
    loading="lazy" style={{float:'left',width:65,height:91,objectFit:'contain',marginRight:12,borderRadius:6}}/>}
    <strong>{entry.card_name||entry.card_id} · #{entry.printed_number||'?'}</strong>
    <div><small>{entry.set_id} · {entry.language.toUpperCase()} · {entry.card_id} · {entry.variant_id}</small></div>
   </div><span>{entry.classification.replaceAll('_',' ')}</span>
  </div>
  <div><strong>Druck:</strong> {entry.print_type||'unbekannt'} {entry.subtype&&' · '+entry.subtype} {entry.foil&&' · '+entry.foil} {entry.stamps&&entry.stamps!=='[]'&&' · '+entry.stamps}</div>
  <div><small>Cardmarket-Set-ID: {entry.provider_expansion_id||'nicht zugeordnet'} · Kandidaten: {entry.candidate_ids.length} · im geprüften Set: {entry.matched_set_ids.length}</small></div>
  <div style={{border:'1px solid var(--border)',borderRadius:10,padding:12,display:'grid',gap:7}}>
    <strong>Warum braucht dieser Fall eine Prüfung?</strong>
    <p style={{margin:0,fontSize:13}}>{detail?.reason||'Die Produkt- und Druckidentität konnte bislang nicht eindeutig bestätigt werden.'}</p>
    <p style={{margin:0,fontSize:13}}><strong>Was du prüfen müsstest:</strong> {detail?.action||'Set, Nummer, Sprache und Holo/Reverse mit der Produktseite vergleichen.'}</p>
    {multipleSimilar&&<p style={{margin:0,fontSize:13}}><strong>Wichtig:</strong> Diese IDs lassen sich anhand der offiziellen Katalogdaten derzeit nicht unterscheiden. Du musst nichts erraten. Ohne zusätzlichen Nachweis bitte nicht bestätigen.</p>}
  </div>
  {detail&&detail.candidates.length>0&&<div style={{display:'grid',gap:8}}><strong>Was das Script gefunden hat</strong>{detail.candidates.map(c=><div key={c.id} style={{border:'1px solid var(--border)',borderRadius:8,padding:10,fontSize:13,display:'flex',gap:12,justifyContent:'space-between',flexWrap:'wrap'}}><div><strong>{c.name}</strong><div>Produkt-ID: {c.id} · Set-ID: {c.expansionId||'unbekannt'}</div><small>Metakarte: {c.metacardId||'unbekannt'} · Katalogeintrag: {c.addedAt||'unbekannt'}</small></div><a href={searchLink(c.id)} rel="noopener noreferrer" target="_blank">Bei Cardmarket suchen</a></div>)}<small>Das Katalogdatum bezeichnet die Aufnahme ins Sortiment, nicht Edition, Druck oder Holo-Variante. Eine Suche ist noch kein Identitätsnachweis.</small></div>}
  {entry.matched_set_ids.length>0?<label style={{display:'grid',gap:6}}>
   <strong>Produkt erst auswählen, wenn du einen eindeutigen Beleg hast</strong>
   <select value={pid} onChange={e=>{setPid(e.target.value);setConfirmed(false)}}>
    <option value="">Bitte auswählen</option>
    {entry.matched_set_ids.map((id,i)=><option key={id} value={id}>{candidate(id)?.name||names[i]||'Produktkandidat'} · Produkt {id}{candidate(id)?.addedAt?' · Aufnahme '+candidate(id)?.addedAt.slice(0,10):''}</option>)}
   </select>
  </label>:<p>Keine verlässliche Produkt-ID im zugeordneten Set. Erst Set/Produkt identifizieren; hier keinen Preis übernehmen.</p>}
  {reference&&<p style={{fontSize:13}}>
   <strong>Offizieller Cardmarket-Guide:</strong> 30 Tage normal {euro(reference.avg30)}
   {' · '}30 Tage Holo {euro(reference.avg30_holo)} · Trend normal {euro(reference.trend)}
   <br/><small>Produktbezogene Referenz, kein sprach-/NM-gefilterter Marktpreis.</small>
  </p>}
  <div className="filterRow">
   <a target="_blank" rel="noopener noreferrer"
    href={'https://www.cardmarket.com/'+entry.language+'/Pokemon/Products/Search?searchString='+encodeURIComponent((entry.card_name||'')+' '+(entry.printed_number||''))}>
    Cardmarket-Suche öffnen
   </a>
  </div>
  <label style={{display:'flex',gap:8,alignItems:'flex-start'}}>
   <input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>
   <span>Ich habe Set, Kartennummer, Sprache, Edition, Holo/Reverse und Sonderdruck auf der Produktseite mit dieser Karte abgeglichen.</span>
  </label>
  <label style={{display:'grid',gap:6}}>Prüfnotiz (optional)
   <input maxLength={500} value={note} onChange={e=>setNote(e.target.value)}
    placeholder="Beleg oder Abweichung notieren"/>
  </label>
  {error&&<p role="alert">{error}</p>}
  <div className="filterRow" style={{gap:10}}>
   <button type="button" className="primaryButton" disabled={busy||!pid||!confirmed}
    onClick={()=>void save('CONFIRMED_PRINT')}>Druckidentität bestätigen</button>
   <button type="button" className="ghostButton" style={buttonStyle} disabled={busy}
    onClick={()=>void save('NO_MATCH')}>Kein passendes Produkt</button>
   <button type="button" className="ghostButton" style={buttonStyle} disabled={busy}
    onClick={()=>void save('DEFERRED')}>Ohne Nachweis zurückstellen</button>
  </div>
  <small>Eine Bestätigung wird als Prüfnachweis gespeichert. Sie veröffentlicht keinen sprachspezifischen NM-Preis.</small>
 </article>;
}
