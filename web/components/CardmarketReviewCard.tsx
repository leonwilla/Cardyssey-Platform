'use client';
import {useState} from 'react';
export type Entry={language:string;card_id:string;variant_id:string;set_id:string;card_name:string;
 printed_number:string;print_type:string;foil:string;subtype:string;stamps:string;
 candidate_ids:string[];matched_set_ids:string[];product_names:string;
 provider_expansion_id:string;classification:string;status:string;
 selected_product_id:string|null;reviewer_note:string|null;
 card_image_url?:string|null;
 diagnosis?:{kind:string;reason:string;action:string;proofAvailable:boolean;sameMetacard:boolean;candidates:{id:string;name:string;expansionId:string;metacardId:string;addedAt:string}[]};
 recheckEvidence?:{category:string;reason:string;versionObserved:string|null;versionProductId:string|null;languageAvailability:string;sameMetacard:boolean;lastScanStatus:string;versionPages?:{version:string;url:string;visualNote:string}[]};
 reference_values?:Record<string,{avg30:number|null;avg30_holo:number|null;trend:number|null;trend_holo:number|null}>;};
type LinkPreview={token:string;productId:string;productUrl:string;productName:string;expansionId:string;pageHeading:string;pageBreadcrumbs:string[];cardName:string;cardNumber:string;cardSet:string;printType:string;warnings:string[];guide:{avg30:number|null;"avg30-holo":number|null;trend:number|null;"trend-holo":number|null};languageSpecificPrice:number|null;languageSpecificPriceStatus:string};
const buttonStyle={padding:'8px 12px'};
export function CardReview({entry,onSaved}:{entry:Entry;onSaved:()=>void}){
 const [pid,setPid]=useState(entry.matched_set_ids.length===1?entry.matched_set_ids[0]:'');
 const [note,setNote]=useState('');
 const [confirmed,setConfirmed]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [manualUrl,setManualUrl]=useState('');
 const [preview,setPreview]=useState<LinkPreview|null>(null);
 const [linkBusy,setLinkBusy]=useState(false);
 const [linkError,setLinkError]=useState('');
 const [linkConfirm,setLinkConfirm]=useState(false);
 const [mismatchConfirm,setMismatchConfirm]=useState(false);
 const names=entry.product_names.split(' | ');
 const detail=entry.diagnosis;
 const candidate=(id:string)=>detail?.candidates.find(c=>c.id===id);
 const multipleSimilar=detail?.kind==='CATALOG_DUPLICATE'&&detail.sameMetacard;
 const productLink=(id:string)=>'https://www.cardmarket.com/Pokemon/Products?idProduct='+encodeURIComponent(id);
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
 async function checkLink(){
  setLinkBusy(true);setLinkError('');setPreview(null);setLinkConfirm(false);setMismatchConfirm(false);
  try{
   const res=await fetch('/api/admin/cardmarket-manual-product',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'preview',language:entry.language,cardId:entry.card_id,variantId:entry.variant_id,url:manualUrl.trim()})});
   const d=await res.json();if(!res.ok)throw Error(d.error||'Produktseite konnte nicht gelesen werden');
   setPreview(d as LinkPreview);
  }catch(e){setLinkError(e instanceof Error?e.message:'Linkprüfung fehlgeschlagen')}
  finally{setLinkBusy(false)}
 }
 async function confirmLink(){
  if(!preview)return;setLinkBusy(true);setLinkError('');
  try{
   const res=await fetch('/api/admin/cardmarket-manual-product',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'confirm',token:preview.token,exactPrintConfirmed:linkConfirm,overrideMismatch:mismatchConfirm,note})});
   const d=await res.json();if(!res.ok)throw Error(d.error||'Zuordnung konnte nicht übernommen werden');
   setPreview(null);setManualUrl('');onSaved();
  }catch(e){setLinkError(e instanceof Error?e.message:'Bestätigung fehlgeschlagen')}
  finally{setLinkBusy(false)}
 }
 const hasMismatch=Boolean(preview?.warnings.some(w=>w.startsWith('SET_ID_CONFLICT')||w.startsWith('PRODUCT_NOT_IN_PREVIOUS_CANDIDATES')));
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
  <div><small>Cardmarket-Set-ID: {entry.provider_expansion_id||'nicht zugeordnet'} · Kandidaten: {entry.candidate_ids.length} · im geprüften Set: {entry.matched_set_ids.length}</small><div style={{fontSize:12,opacity:.8}}>Die Anzeige „{entry.language.toUpperCase()}“ ist die gesuchte Preissprache, kein Nachweis einer entsprechenden physischen Kartenausgabe. Bitte Kartennummer und tatsächliche Karte im verlinkten Produkt prüfen.</div></div>
  {entry.recheckEvidence&&<div style={{border:'1px solid var(--border)',borderRadius:10,padding:12,display:'grid',gap:5,fontSize:13}}><strong>Ergebnis der erneuten automatischen Prüfung</strong><div>{entry.recheckEvidence.reason}</div>{entry.recheckEvidence.versionObserved&&<div>Nachgewiesene URL-Version: <strong>{entry.recheckEvidence.versionObserved}</strong> · Produkt {entry.recheckEvidence.versionProductId}. Das beweist noch nicht Normal/Holo.</div>}<div>Deutsche/englische Angebote: {entry.recheckEvidence.languageAvailability==='OFFERS_OBSERVED'?'In der ausgewählten Sprache bei früherem Scan beobachtet':'Noch nicht nachgewiesen – nicht automatisch ausgeschlossen'}</div>{entry.recheckEvidence.versionPages?.map(p=><div key={p.version}><a href={p.url} target="_blank" rel="noopener noreferrer">Cardmarket-Seite {p.version} ansehen</a> <small>({p.visualNote==='holographic-looking artwork'?'Bild wirkt holografisch':'Bild wirkt normal'})</small></div>)}<small>Scanstatus: {entry.recheckEvidence.lastScanStatus.replaceAll('_',' ')}</small></div>}
  <div style={{border:'1px solid var(--border)',borderRadius:10,padding:12,display:'grid',gap:7}}>
    <strong>Warum braucht dieser Fall eine Prüfung?</strong>
    <p style={{margin:0,fontSize:13}}>{detail?.reason||'Die Produkt- und Druckidentität konnte bislang nicht eindeutig bestätigt werden.'}</p>
    <p style={{margin:0,fontSize:13}}><strong>Was du prüfen müsstest:</strong> {detail?.action||'Set, Nummer, Sprache und Holo/Reverse mit der Produktseite vergleichen.'}</p>
    {multipleSimilar&&<p style={{margin:0,fontSize:13}}><strong>Wichtig:</strong> Diese IDs lassen sich anhand der offiziellen Katalogdaten derzeit nicht unterscheiden. Öffne jede ID über den Direktlink und vergleiche die dort angezeigte Kartennummer sowie V1/V2. Ohne eindeutigen Nachweis bitte nicht bestätigen.</p>}
  </div>
  {detail&&detail.candidates.length>0&&<div style={{display:'grid',gap:8}}><strong>Was das Script gefunden hat</strong>{detail.candidates.map(c=><div key={c.id} style={{border:'1px solid var(--border)',borderRadius:8,padding:10,fontSize:13,display:'flex',gap:12,justifyContent:'space-between',flexWrap:'wrap'}}><div><strong>{c.name}</strong><div>Produkt-ID: {c.id} · Set-ID: {c.expansionId||'unbekannt'}</div><small>Metakarte: {c.metacardId||'unbekannt'} · Katalogeintrag: {c.addedAt||'unbekannt'}</small></div><div style={{display:'grid',gap:6,justifyItems:'end'}}><a href={productLink(c.id)} rel="noopener noreferrer" target="_blank" style={{fontWeight:700}}>Produkt {c.id} direkt öffnen</a><a href={searchLink(c.id)} rel="noopener noreferrer" target="_blank" style={{fontSize:12}}>Allgemeine Suche (kein ID-Nachweis)</a></div></div>)}<small>Die Direktlinks enthalten die exakte Produkt-ID als <code>idProduct=…</code>. Nach dem Öffnen kann Cardmarket auf eine lesbare URL ohne Zahl weiterleiten – der Direktlink bleibt trotzdem eindeutig. Die allgemeine Suche ist ausdrücklich kein ID-Nachweis. Vergleiche außerdem Set und Kartennummer: Gleichnamige Produkte können zu unterschiedlichen Sets gehören.</small></div>}
  <section style={{border:'1px solid var(--border)',borderRadius:12,padding:14,display:'grid',gap:9}}>
   <strong>Richtigen Cardmarket-Produktlink selbst eintragen</strong>
   <p style={{fontSize:13,margin:0}}>Wenn die vorgeschlagenen Produkte nicht passen: Öffne die richtige Karte auf Cardmarket, kopiere die vollständige Produkt-URL hier hinein und lasse die Seite prüfen. Die Prüfung ändert noch keinen Preis und keine Zuordnung.</p>
   <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
    <input style={{flex:'1 1 320px',minWidth:0}} value={manualUrl} onChange={e=>setManualUrl(e.target.value)} placeholder="https://www.cardmarket.com/de/Pokemon/Products/Singles/…" aria-label="Korrekten Cardmarket-Produktlink eingeben" />
    <button type="button" className="primaryButton" disabled={linkBusy||!manualUrl.trim()} onClick={()=>void checkLink()}>{linkBusy?'Prüft Produktseite …':'Produktlink prüfen und Vorschau öffnen'}</button>
   </div>
   {linkError&&<p role="alert" style={{fontSize:13,color:'var(--danger,#a22)',margin:0}}>{linkError==='cardmarket_cloudflare_blocked_try_later'?'Cardmarket zeigt aktuell eine Cloudflare-Prüfung. Der Link wurde nicht zugeordnet. Bitte später erneut prüfen.':linkError}</p>}
  </section>
  {preview&&<div role="presentation" style={{position:'fixed',inset:0,zIndex:1000,background:'rgba(0,0,0,.65)',display:'grid',placeItems:'center',padding:16}}>
   <section role="dialog" aria-modal="true" aria-label="Cardmarket-Produktprüfung bestätigen" style={{maxWidth:650,width:'100%',maxHeight:'88vh',overflowY:'auto',background:'var(--surface,#fff)',color:'var(--text,#17231b)',borderRadius:14,padding:22,display:'grid',gap:12}}>
    <h3 style={{margin:0}}>Cardmarket-Produktprüfung – Vorschau</h3>
    <div><strong>Deine Karte:</strong> {preview.cardName} #{preview.cardNumber} · Set {preview.cardSet} · {entry.language.toUpperCase()} · {preview.printType}</div>
    <div><strong>Auf Cardmarket gefunden:</strong> {preview.productName}<div>ID: <strong>{preview.productId}</strong> · Cardmarket-Set-ID: {preview.expansionId}</div><div>Seitenüberschrift: {preview.pageHeading||'Keine lesbare Überschrift'}</div><div>{preview.pageBreadcrumbs?.join(' / ')}</div><a href={preview.productUrl} target="_blank" rel="noopener noreferrer">Geprüfte Produktseite öffnen</a></div>
    <div style={{fontSize:13}}><strong>Offizieller Preisguide (nur Referenz):</strong> 30 Tage normal {euro(preview.guide?.avg30)} · Holo {euro(preview.guide?.['avg30-holo'])}<div><strong>Preis für {entry.language.toUpperCase()} / NM / exakten Druck:</strong> Noch nicht verifiziert. Erst nach gefiltertem Scan verfügbar.</div></div>
    <div style={{display:'grid',gap:5,fontSize:13}}><strong>Wichtige Prüfhinweise</strong>{preview.warnings.map((w,i)=><div key={i}>• {w.replace('SET_ID_CONFLICT: ','Set-Konflikt: ').replace('PRODUCT_NOT_IN_PREVIOUS_CANDIDATES: ','Neuer Produktkandidat: ').replace('PRINT_UNVERIFIED: ','Druckprüfung: ').replace('LANGUAGE_UNVERIFIED: ','Sprache: ')}</div>)}</div>
    <label style={{display:'flex',gap:8,fontSize:13}}><input type="checkbox" checked={linkConfirm} onChange={e=>setLinkConfirm(e.target.checked)}/>Ich habe das Kartenbild, Set, die gedruckte Nummer, Edition, Holo/Reverse und Sprache selbst verglichen. Dieser Link gehört genau zur angezeigten Kartenvariante.</label>
    {hasMismatch&&<label style={{display:'flex',gap:8,fontSize:13}}><input type="checkbox" checked={mismatchConfirm} onChange={e=>setMismatchConfirm(e.target.checked)}/>Der bisherige automatische Kandidat/Set-Abgleich ist falsch oder unvollständig. Ich bestätige die abweichende Zuordnung ausdrücklich.</label>}
    <div style={{display:'flex',justifyContent:'flex-end',flexWrap:'wrap',gap:10}}><button type="button" className="ghostButton" disabled={linkBusy} onClick={()=>setPreview(null)}>Abbrechen</button><button type="button" className="primaryButton" disabled={linkBusy||!linkConfirm||(hasMismatch&&!mismatchConfirm)} onClick={()=>void confirmLink()}>{linkBusy?'Speichert …':'Zuordnung bestätigen und als Lernbeispiel speichern'}</button></div>
    {linkError&&<p role="alert" style={{fontSize:13}}>{linkError}</p>}
   </section>
  </div>}
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
