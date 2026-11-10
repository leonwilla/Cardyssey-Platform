'use client';
import {useState} from 'react';
export type Entry={language:string;card_id:string;variant_id:string;set_id:string;set_name?:string;card_name:string;
 printed_number:string;print_type:string;foil:string;subtype:string;stamps:string;
 candidate_ids:string[];matched_set_ids:string[];product_names:string;
 provider_expansion_id:string;classification:string;status:string;
 selected_product_id:string|null;reviewer_note:string|null;
 card_image_url?:string|null;version_product_images?:{id:string;version:string;url:string;imageUrl:string;evidence:string}[];version_page_url?:string|null;version_family_product_count?:number;version_same_expansion_ids?:string[];related_sets?:{set_id:string;set_name:string;card_id:string;printed_number:string}[];suggested_product_url?:string|null;
 diagnosis?:{kind:string;reason:string;action:string;proofAvailable:boolean;sameMetacard:boolean;candidates:{id:string;name:string;expansionId:string;metacardId:string;addedAt:string}[]};
 recheckEvidence?:{category:string;reason:string;versionObserved:string|null;versionProductId:string|null;languageAvailability:string;sameMetacard:boolean;lastScanStatus:string;versionPages?:{version:string;url:string;visualNote:string}[]};
 reference_values?:Record<string,{avg30:number|null;avg30_holo:number|null;trend:number|null;trend_holo:number|null}>;};
type LinkPreview={token:string;productId:string;productUrl:string;productName:string;expansionId:string;pageHeading:string;pageBreadcrumbs:string[];cardName:string;cardNumber:string;cardSet:string;printType:string;warnings:string[];guide:{avg30:number|null;"avg30-holo":number|null;trend:number|null;"trend-holo":number|null};languageSpecificPrice:number|null;languageSpecificPriceStatus:string};
export function CardReview({entry,onSaved,onViewRelated,scanIssue}:{entry:Entry;onSaved:()=>void;onViewRelated?:(cardId:string)=>void;scanIssue?:{status:string;detail:string}}){
 const [pid,setPid]=useState(entry.matched_set_ids.length===1?entry.matched_set_ids[0]:'');
 const [note,setNote]=useState('');
 const [detailsOpen,setDetailsOpen]=useState(false);
 const [imageFailed,setImageFailed]=useState(false);
 const [otherActionsOpen,setOtherActionsOpen]=useState(false);
 const [confirmed,setConfirmed]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [manualUrl,setManualUrl]=useState('');
 const [preview,setPreview]=useState<LinkPreview|null>(null);
 const [linkBusy,setLinkBusy]=useState(false);
 const [undoBusy,setUndoBusy]=useState(false);
 const [linkError,setLinkError]=useState('');
 const [linkConfirm,setLinkConfirm]=useState(false);
 const [mismatchConfirm,setMismatchConfirm]=useState(false);
 const names=entry.product_names.split(' | ');
 const detail=entry.diagnosis;
 const candidate=(id:string)=>detail?.candidates.find(c=>c.id===id);
 const multipleSimilar=detail?.kind==='CATALOG_DUPLICATE'&&detail.sameMetacard;
 const productLink=(id:string)=>'https://www.cardmarket.com/Pokemon/Products?idProduct='+encodeURIComponent(id);
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
 async function undoDecision(){
  if(!window.confirm('Diese Entscheidung für '+entry.card_name+' ('+entry.set_id+' / '+entry.print_type+') zurücknehmen? Die Karte wird wieder offen. Bereits gespeicherte unabhängige Preise bleiben bestehen.'))return;
  setUndoBusy(true);setError('');
  try{
   const r=await fetch('/api/admin/cardmarket-print-review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'undo',language:entry.language,cardId:entry.card_id,variantId:entry.variant_id})});
   const data=await r.json();if(!r.ok)throw Error(data.error||'Rückgängig nicht möglich');
   onSaved();
  }catch(e){setError(e instanceof Error?e.message:'Rückgängig fehlgeschlagen')}
  finally{setUndoBusy(false)}
 }
 const hasMismatch=Boolean(preview?.warnings.some(w=>w.startsWith('SET_ID_CONFLICT')||w.startsWith('PRODUCT_NOT_IN_PREVIOUS_CANDIDATES')));
 const shortIssue=()=>{
  const status=scanIssue?.status||entry.recheckEvidence?.lastScanStatus||'';
  if(status==='PRODUCT_ID_NOT_VERIFIED_FOR_CARD'||status==='PRODUCT_ID_NOT_IN_VERIFIED_SET')return 'Produkt-ID passt noch nicht sicher zu Set und Kartennummer.';
  if(status==='NO_EXACT_NUMBER_SEARCH_HIT')return 'Keine eindeutige Karte zur Kartennummer gefunden.';
  if(status==='SET_MAPPING_PENDING'||entry.classification.includes('SET_NOT_VERIFIED'))return 'Cardmarket-Set noch nicht sicher zugeordnet.';
  if(status==='PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED'||entry.classification.includes('PRINT_NOT_IDENTIFIED'))return 'Karte gefunden – genaue Druckvariante noch offen.';
  if(status==='MISSING_REQUIRED_SCAN_FIELDS')return 'Für die automatische Zuordnung fehlen Angaben.';
  if(status==='FILTER_UNAVAILABLE'||status==='FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE')return 'Preisfilter nicht vollständig auslesbar – keine Kartenbestätigung erforderlich.';
  if(entry.matched_set_ids.length>1)return 'Mehrere mögliche Produktversionen – richtige Variante auswählen.';
  if(entry.matched_set_ids.length===1)return 'Kartenvariante noch nicht eindeutig bestätigt.';
  return 'Cardmarket-Produkt oder Set noch nicht eindeutig gefunden.';
 };
 const variantLabel=[entry.stamps&&entry.stamps!=='[]'?(()=>{try{const v=JSON.parse(entry.stamps);return Array.isArray(v)?v.join(', '):entry.stamps}catch{return entry.stamps}})():null,entry.foil||null,entry.subtype||null].filter(Boolean).join(' · ')||entry.print_type;
 const searchUrl='https://www.cardmarket.com/'+entry.language+'/Pokemon/Products/Search?searchString='+encodeURIComponent((entry.card_name||'')+' '+(entry.printed_number||''));
 return <article className="statusPanel" style={{padding:14,display:'grid',gap:12}}>
  <div style={{display:'flex',alignItems:'center',gap:12,flexWrap:'wrap'}}>
   <div style={{width:88,minWidth:88,display:'grid',gap:4,textAlign:'center'}}>
    {entry.card_image_url?.startsWith('https://')&&!imageFailed?<img src={entry.card_image_url} onError={()=>setImageFailed(true)} alt={'Grundkartenbild '+entry.card_name} loading="lazy" style={{width:88,height:120,objectFit:'contain',borderRadius:7}}/>:<div style={{width:88,height:120,border:'1px dashed var(--border)',borderRadius:7,display:'grid',placeItems:'center',fontSize:11}}>Kein Bild verfügbar</div>}
    <span style={{fontSize:10,opacity:.7}}>Grundkartenbild</span>
   </div>
   <div style={{flex:'1 1 210px',minWidth:0}}><strong>{entry.card_name||entry.card_id} · #{entry.printed_number||'?'}</strong>
    <div style={{fontSize:12,opacity:.75}}>{entry.set_name||entry.set_id} ({entry.set_id}) · {entry.language.toUpperCase()} · {entry.print_type}</div><div style={{fontSize:13,marginTop:4}}><strong>Gesuchte Variante:</strong> {variantLabel}</div><div style={{fontSize:11,opacity:.7}}>Hinweis: Das Grundkartenbild muss den seltenen Stempel nicht zeigen.</div>
    <div style={{fontSize:13,marginTop:5}}><strong>Problem:</strong> {shortIssue()}</div>
   </div>
   <button type="button" className="ghostButton" onClick={()=>setDetailsOpen(v=>!v)}>{detailsOpen?'Details schließen':'Details'}</button>
  </div>
  {entry.status!=='PENDING_REVIEW'?<div style={{display:'grid',gap:8}}>
   <div><strong>{entry.status==='CONFIRMED_PRINT'?'Bestätigte Zuordnung':entry.status==='NO_MATCH'?'Kein Treffer':'Zurückgestellt'}</strong>{entry.selected_product_id?' · Produkt '+entry.selected_product_id:''}</div>
   {entry.reviewer_note&&<small>{entry.reviewer_note}</small>}
   <button type="button" className="ghostButton" disabled={undoBusy} onClick={()=>void undoDecision()}>{undoBusy?'Wird zurückgenommen …':'Zuordnung rückgängig machen'}</button>
   {error&&<p role="alert">{error}</p>}
  </div>:<>
   <div style={{display:'grid',gap:7}}>
    <strong style={{fontSize:13}}>Gefundene Cardmarket-Produktseiten</strong>
    {entry.version_product_images?.length? <div style={{display:'flex',gap:10,flexWrap:'wrap'}}>
      {entry.version_product_images.map(v=><div key={v.id} style={{width:130,border:'1px solid var(--border)',borderRadius:9,padding:8,display:'grid',gap:5,justifyItems:'center'}}>
        <img src={v.imageUrl} alt={'Cardmarket '+v.version+' Produkt '+v.id} loading="lazy" style={{width:95,height:135,objectFit:'contain'}}/>
        <strong style={{fontSize:12}}>{v.version} · ID {v.id}</strong>
        <a href={v.url} target="_blank" rel="noopener noreferrer" style={{fontSize:12}}>Produkt ansehen</a>
      </div>)}
      <small style={{width:'100%',opacity:.8}}>Zwei Produktversionen im selben Set. Bilder dienen dem Vergleich – Sonderstempel und Holo-Muster sind dadurch noch nicht automatisch bestätigt.</small>
    </div>:entry.matched_set_ids.length>0?<div style={{display:'flex',gap:8,flexWrap:'wrap'}}>{entry.matched_set_ids.map(id=><a key={id} href={productLink(id)} target="_blank" rel="noopener noreferrer" style={{fontSize:13,padding:'8px 10px',border:'1px solid var(--border)',borderRadius:9,fontWeight:600}}>Produkt {id} ansehen</a>)}</div>:<span style={{fontSize:13,opacity:.75}}>Kein geprüfter Produktlink gefunden.</span>}
    {entry.suggested_product_url&&<div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}><a href={entry.suggested_product_url} target="_blank" rel="noopener noreferrer" style={{fontSize:13,fontWeight:600}}>{entry.matched_set_ids.length>1?'Produktkandidat öffnen (Druck noch offen)':'Gefundene Produktseite öffnen'}</a><button type="button" className="ghostButton" onClick={()=>setManualUrl(entry.suggested_product_url||'')}>Link übernehmen</button></div>}
    {entry.version_page_url&&<a href={entry.version_page_url} target="_blank" rel="noopener noreferrer" style={{fontSize:13,fontWeight:600}}>Alle Druckversionen auf Cardmarket vergleichen</a>}
    {Boolean(entry.version_family_product_count)&&<small style={{opacity:.75}}>Automatisch erkannte Reprint-Familie: {entry.version_family_product_count} Katalogprodukte{entry.version_same_expansion_ids?.length?' · davon '+entry.version_same_expansion_ids.length+' im bestätigten Set':''}. Ähnliche Reprints aus fremden Sets werden nicht als dieselbe Karte bestätigt.</small>}
    <a href={searchUrl} target="_blank" rel="noopener noreferrer" style={{fontSize:13}}>Auf Cardmarket suchen</a>
   </div>
   <section style={{display:'grid',gap:8}}>
    <strong style={{fontSize:13}}>Richtigen Link eintragen</strong>
    <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
     <input style={{flex:'1 1 280px',minWidth:0}} value={manualUrl} onChange={e=>setManualUrl(e.target.value)} placeholder="Cardmarket-Produktlink hier einfügen …" aria-label="Cardmarket-Produktlink" />
     <button type="button" className="primaryButton" disabled={linkBusy||!manualUrl.trim()} onClick={()=>void checkLink()}>{linkBusy?'Prüft …':'Link prüfen'}</button>
    </div>
    {linkError&&<p role="alert" style={{fontSize:13,margin:0,color:'var(--danger,#a22)'}}>{linkError==='cardmarket_cloudflare_blocked_try_later'?'Cardmarket durch Cloudflare blockiert. Link nicht gespeichert.':linkError.startsWith('wrong_set_url_expected_')?'Falsches Set: Der Link gehört nicht zu '+(linkError.replace('wrong_set_url_expected_','').replaceAll('-',' '))+'. Bitte die vorgeschlagene Produktseite für '+entry.set_id+' verwenden.':linkError==='resolved_product_belongs_to_other_set'?'Der Link führt zu einer Karte aus einem anderen Set. Bitte den passenden Set-Link verwenden.':linkError}</p>}
   </section>
   {entry.matched_set_ids.length>0&&<label style={{display:'grid',gap:5,fontSize:13}}><strong>Richtiges Produkt wählen</strong>
    <select aria-label="Cardmarket-Produkt wählen" value={pid} onChange={e=>{setPid(e.target.value);setConfirmed(false)}}>
     <option value="">Produkt auswählen</option>
     {entry.matched_set_ids.map((id,i)=><option value={id} key={id}>{candidate(id)?.name||names[i]||entry.card_name} {entry.version_product_images?.find(v=>v.id===id)?.version||''} · ID {id}</option>)}
    </select>
   </label>}
   {entry.matched_set_ids.length>0&&<label style={{display:'flex',gap:8,alignItems:'flex-start',fontSize:13}}><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/><span>Ich habe Karte, Set, Nummer, Sprache und genaue Druckvariante verglichen.</span></label>}
   {error&&<p role="alert">{error}</p>}
   <div style={{display:'flex',gap:8,flexWrap:'wrap',alignItems:'center'}}>
    {entry.matched_set_ids.length>0&&<button type="button" className="primaryButton" disabled={busy||!pid||!confirmed} onClick={()=>void save('CONFIRMED_PRINT')}>{busy?'Speichert …':'Zuordnung bestätigen'}</button>}
    <button type="button" className="ghostButton" onClick={()=>setOtherActionsOpen(v=>!v)}>{otherActionsOpen?'Weitere Aktionen schließen':'Weitere Aktionen'}</button>
   </div>
   {otherActionsOpen&&<div style={{display:'flex',gap:8,flexWrap:'wrap'}}><button type="button" className="ghostButton" disabled={busy} onClick={()=>void save('NO_MATCH')}>Kein passendes Produkt</button><button type="button" className="ghostButton" disabled={busy} onClick={()=>void save('DEFERRED')}>Zurückstellen</button></div>}
   {detailsOpen&&<section style={{padding:12,border:'1px solid var(--border)',borderRadius:10,display:'grid',gap:8,fontSize:12}}>
    <strong>Technische Details</strong>
    <div>Cardyssey-ID: {entry.card_id} · Variante: {entry.variant_id}</div>
    <div>Cardmarket-Set-ID: {entry.provider_expansion_id||'nicht zugeordnet'} · Kandidaten: {entry.matched_set_ids.length}</div>
    <div>{detail?.reason||entry.recheckEvidence?.reason||'Automatische Identitätsprüfung noch offen.'}</div>
    {scanIssue?.detail&&<div>Scanner: {scanIssue.status} · {scanIssue.detail}</div>}
    {entry.recheckEvidence?.versionObserved&&<div>URL-Version: {entry.recheckEvidence.versionObserved} · Produkt {entry.recheckEvidence.versionProductId}</div>}
    {detail?.action&&<div>Prüfhinweis: {detail.action}</div>}
    {multipleSimilar&&<div>Ähnlich benannte Produkte können verschiedene Ausgaben sein. Nur anhand eindeutiger Druckmerkmale bestätigen.</div>}
    <label style={{display:'grid',gap:5}}>Prüfnotiz (optional)<input maxLength={500} value={note} onChange={e=>setNote(e.target.value)} placeholder="Dein Nachweis / deine Anmerkung"/></label>
    <small>Keine Preise werden durch eine reine Produktzuordnung veröffentlicht.</small>
   </section>}
  </>}
  {preview&&<div role="presentation" style={{position:'fixed',inset:0,zIndex:1000,background:'rgba(0,0,0,.65)',display:'grid',placeItems:'center',padding:16}}>
   <section role="dialog" aria-modal="true" aria-label="Cardmarket-Produktprüfung bestätigen" style={{maxWidth:650,width:'100%',maxHeight:'88vh',overflowY:'auto',background:'var(--surface,#fff)',color:'var(--text,#17231b)',borderRadius:14,padding:22,display:'grid',gap:12}}>
    <h3 style={{margin:0}}>Produktlink bestätigen</h3>
    <div style={{fontSize:13}}><strong>Deine Karte:</strong> {preview.cardName} · #{preview.cardNumber} · {preview.cardSet} · {preview.printType}</div>
    <div style={{fontSize:13}}><strong>Gefunden:</strong> {preview.productName} · Produkt {preview.productId}<div><a href={preview.productUrl} target="_blank" rel="noopener noreferrer">Produktseite öffnen und vergleichen</a></div></div>
    {preview.warnings.length>0&&<div style={{fontSize:12,display:'grid',gap:4}}>{preview.warnings.map((w,i)=><div key={i}>{w.replace('SET_ID_CONFLICT: ','Set-Konflikt: ').replace('PRODUCT_NOT_IN_PREVIOUS_CANDIDATES: ','Neuer Produktkandidat: ').replace('PRINT_UNVERIFIED: ','Druck noch nicht geprüft: ').replace('LANGUAGE_UNVERIFIED: ','Sprache noch nicht geprüft: ')}</div>)}</div>}
    <label style={{display:'flex',gap:8,fontSize:13}}><input type="checkbox" checked={linkConfirm} onChange={e=>setLinkConfirm(e.target.checked)}/>Ich habe das Kartenbild, Set, die gedruckte Nummer, Edition, Holo/Reverse und Sprache selbst verglichen. Dieser Link gehört genau zur angezeigten Kartenvariante.</label>
    {hasMismatch&&<label style={{display:'flex',gap:8,fontSize:13}}><input type="checkbox" checked={mismatchConfirm} onChange={e=>setMismatchConfirm(e.target.checked)}/>Der bisherige automatische Kandidat/Set-Abgleich ist falsch oder unvollständig. Ich bestätige die abweichende Zuordnung ausdrücklich.</label>}
    <div style={{display:'flex',justifyContent:'flex-end',flexWrap:'wrap',gap:10}}><button type="button" className="ghostButton" disabled={linkBusy} onClick={()=>setPreview(null)}>Abbrechen</button><button type="button" className="primaryButton" disabled={linkBusy||!linkConfirm||(hasMismatch&&!mismatchConfirm)} onClick={()=>void confirmLink()}>{linkBusy?'Speichert …':'Link bestätigen'}</button></div>
    {linkError&&<p role="alert" style={{fontSize:13}}>{linkError}</p>}
   </section>
  </div>}
 </article>;
}
