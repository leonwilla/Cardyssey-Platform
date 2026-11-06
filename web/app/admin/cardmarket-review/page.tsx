'use client';
import {useCallback,useEffect,useState} from 'react';
import {useRouter} from 'next/navigation';
import {AppShell} from '@/components/AppShell';
import type {User} from '@/lib/types';

type Entry={language:string;card_id:string;variant_id:string;set_id:string;card_name:string;
 printed_number:string;print_type:string;foil:string;subtype:string;stamps:string;
 candidate_ids:string[];matched_set_ids:string[];product_names:string;
 provider_expansion_id:string;classification:string;status:string;
 selected_product_id:string|null;reviewer_note:string|null;
 card_image_url?:string|null;
 reference_values?:Record<string,{avg30:number|null;avg30_holo:number|null;trend:number|null;trend_holo:number|null}>;};
type Result={total:number;items:Entry[];guide_date?:string};
const initial:Result={total:0,items:[]};
const buttonStyle={padding:'8px 12px'};
function CardReview({entry,onSaved}:{entry:Entry;onSaved:()=>void}){
 const [pid,setPid]=useState(entry.matched_set_ids.length===1?entry.matched_set_ids[0]:'');
 const [note,setNote]=useState('');
 const [confirmed,setConfirmed]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const names=entry.product_names.split(' | ');
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
  {entry.matched_set_ids.length>0?<label style={{display:'grid',gap:6}}>
   <strong>Produkt im passenden Set auswählen</strong>
   <select value={pid} onChange={e=>{setPid(e.target.value);setConfirmed(false)}}>
    <option value="">Bitte auswählen</option>
    {entry.matched_set_ids.map((id,i)=><option key={id} value={id}>{id} · {names[i]||'Produktkandidat'}</option>)}
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
    onClick={()=>void save('DEFERRED')}>Später prüfen</button>
  </div>
  <small>Eine Bestätigung wird als Prüfnachweis gespeichert. Sie veröffentlicht keinen sprachspezifischen NM-Preis.</small>
 </article>;
}
export default function CardmarketReviewPage(){
 const router=useRouter();
 const [user,setUser]=useState<User|null>(null);
 const [language,setLanguage]=useState('de');
 const [status,setStatus]=useState('PENDING_REVIEW');
 const [search,setSearch]=useState('');
 const [page,setPage]=useState(0);
 const [result,setResult]=useState<Result>(initial);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 const reload=useCallback(async()=>{
  if(!user)return;
  setLoading(true);setError('');
  try{
   const params=new URLSearchParams({language,status,search,page:String(page)});
   const r=await fetch('/api/admin/cardmarket-print-review?'+params,{cache:'no-store'});
   if(!r.ok)throw Error('Prüfliste konnte nicht geladen werden');
   setResult(await r.json());
  }catch(e){setError(e instanceof Error?e.message:'Fehler')}
  finally{setLoading(false)}
 },[user,language,status,search,page]);
 useEffect(()=>{fetch('/api/auth/me',{cache:'no-store'}).then(async r=>{
  if(!r.ok){router.replace('/login');return}
  const data=await r.json() as User;
  if(!data.canAdmin&&data.role!=='ADMIN'&&data.role!=='FOUNDER'){router.replace('/account');return}
  setUser(data);
 }).catch(()=>router.replace('/login'))},[router]);
 useEffect(()=>{void reload()},[reload]);
 return <AppShell active="/admin/prices" user={user}>
  <section className="pageIntro"><div>
   <span className="eyebrowText">Admin · Cardmarket</span>
   <h1>Druckvarianten zuordnen</h1>
   <p>Offizielle Produktkandidaten aus dem Cardmarket-Katalog prüfen. Der öffentliche Preisguide liefert keinen garantiert sprach- und zustandsspezifischen NM-Wert.</p>
  </div></section>
  <div className="filterRow" style={{gap:10,marginBottom:18}}>
   <button className="ghostButton" onClick={()=>router.push('/admin/prices')}>← Preisübersicht</button>
   <select aria-label="Sprache" value={language} onChange={e=>{setLanguage(e.target.value);setPage(0)}}>
    <option value="de">Deutsch</option><option value="en">Englisch</option>
   </select>
   <select aria-label="Prüfstatus" value={status} onChange={e=>{setStatus(e.target.value);setPage(0)}}>
    <option value="PENDING_REVIEW">Offen</option><option value="CONFIRMED_PRINT">Bestätigt</option>
    <option value="DEFERRED">Zurückgestellt</option><option value="NO_MATCH">Kein Treffer</option>
    <option value="ALL">Alle</option>
   </select>
   <input aria-label="Karte suchen" placeholder="Karte, Nummer oder Set suchen" value={search}
    onChange={e=>{setSearch(e.target.value);setPage(0)}}/>
   <button className="ghostButton" onClick={()=>void reload()}>Aktualisieren</button>
  </div>
  <p>{loading?'Wird geladen …':result.total.toLocaleString('de-DE')+' Prüffälle'} · Seite {page+1}
  {result.guide_date&&<small> · Preisguide: {result.guide_date}</small>}</p>
  {error&&<p role="alert">{error}</p>}
  <div style={{display:'grid',gap:12}}>
   {result.items.map(item=><CardReview key={item.language+item.card_id+item.variant_id} entry={item} onSaved={()=>void reload()}/>)}
  </div>
  <div className="filterRow" style={{gap:10,marginTop:18}}>
   <button className="ghostButton" disabled={page===0} onClick={()=>setPage(p=>Math.max(0,p-1))}>← Zurück</button>
   <button className="ghostButton" disabled={(page+1)*50>=result.total} onClick={()=>setPage(p=>p+1)}>Weitere 50 →</button>
  </div>
 </AppShell>;
}
