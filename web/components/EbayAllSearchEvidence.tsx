'use client';
import {useEffect,useMemo,useState} from 'react';

type Kind='CONFIRMED_SINGLE'|'MULTI_SELECTION'|'OTHER_CARD'|'COLLECTOR_EXCLUDED'|'IDENTITY_UNCLEAR';
type SearchItem={itemId:string;title:string;url?:string|null;soldDate?:string|null;displayedPrice?:number|null;imageUrl?:string|null;kind:Kind;collectorExclusions:string;imageVerified:boolean};
type Transaction={variant:string;displayedPrice:string;quantity:string;purchasedAt:string};
type Offer={itemId:string;title:string;url:string;displayedPrice?:number|null;purchaseStatus?:string|null;transactions:Transaction[]};
type Evidence={cardId:string;run:string;query?:string;totalSearchResults:number;counts:Record<Kind,number>;results:SearchItem[];offers:Offer[]};
const categories:{key:Kind| 'ALL';label:string}[]=[{key:'ALL',label:'Alle'},{key:'CONFIRMED_SINGLE',label:'Passende Einzelverkäufe'},{key:'MULTI_SELECTION',label:'Mehrfachauswahl'},{key:'OTHER_CARD',label:'Andere Karten'},{key:'IDENTITY_UNCLEAR',label:'Unklar'},{key:'COLLECTOR_EXCLUDED',label:'Ausgeschlossen'}];
const kindText:Record<Kind,string>={CONFIRMED_SINGLE:'Passender Einzelverkauf',MULTI_SELECTION:'Mehrfachauswahl – Variante noch zu prüfen',OTHER_CARD:'Andere Karte',COLLECTOR_EXCLUDED:'Vom Collector ausgeschlossen',IDENTITY_UNCLEAR:'Kartenzuordnung unklar'};
const money=(x:number|null|undefined)=>x==null?'Preis nicht erfasst':new Intl.NumberFormat('de-DE',{style:'currency',currency:'EUR'}).format(x);
export function EbayAllSearchEvidence({cardId}:{cardId:string}){
 const [data,setData]=useState<Evidence|null>(null);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 const [expanded,setExpanded]=useState(false);
 const [tab,setTab]=useState<'search'|'purchases'>('search');
 const [kind,setKind]=useState<Kind|'ALL'>('ALL');
 const [query,setQuery]=useState('');
 useEffect(()=>{setData(null);setExpanded(false);setError('');setKind('ALL');setQuery('')},[cardId]);
 async function load(){setLoading(true);setError('');try{
  const response=await fetch('/api/admin/price-card-evidence?cardId='+encodeURIComponent(cardId),{cache:'no-store'});
  if(!response.ok)throw new Error('Die gespeicherten Treffer konnten nicht geladen werden.');
  setData(await response.json() as Evidence);setExpanded(true);
 }catch(e){setError(e instanceof Error?e.message:'Abruf fehlgeschlagen')}finally{setLoading(false)}}
 const items=useMemo(()=>data?.results.filter(x=>(kind==='ALL'||x.kind===kind)&&[x.title,x.itemId,x.collectorExclusions].join(' ').toLowerCase().includes(query.toLowerCase()))??[],[data,kind,query]);
 return <section style={{marginTop:16,padding:16,border:'1px solid var(--border)',borderRadius:14}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center',flexWrap:'wrap'}}>
   <div><strong>Alle eBay-Treffer und Kauftransaktionen</strong><p style={{fontSize:12,margin:'5px 0 0'}}>Vollständige gespeicherte Prüfliste, einschließlich anderer Karten und abgelehnter Anzeigen.</p></div>
   <button type="button" className="ghostButton" disabled={loading} onClick={()=>{if(data){setExpanded(!expanded)}else void load()}}>{loading?'Lädt …':data?(expanded?'Liste schließen':'Alle Treffer öffnen'):'Alle Treffer anzeigen'}</button>
  </div>
  {error&&<p role="alert">{error} <button onClick={()=>void load()} type="button">Erneut laden</button></p>}
  {expanded&&data&&<div style={{marginTop:16,display:'grid',gap:12}}>
   <div style={{display:'flex',flexWrap:'wrap',gap:10}}>
    <span><strong>{data.totalSearchResults}</strong> eBay-Suchtreffer (nicht Kartenverkäufe)</span>
    <span>· <strong>{data.counts.CONFIRMED_SINGLE}</strong> passende Einzelverkäufe</span>
    <span>· <strong>{data.counts.MULTI_SELECTION}</strong> Auswahlangebote</span>
    <span>· <strong>{data.counts.OTHER_CARD}</strong> andere Karten</span>
    <span>· <strong>{data.counts.IDENTITY_UNCLEAR+data.counts.COLLECTOR_EXCLUDED}</strong> unklar/ausgeschlossen</span>
   </div>
   <div className="filterRow"><button type="button" className={tab==='search'?'primaryButton':'ghostButton'} onClick={()=>setTab('search')}>Alle Suchtreffer ({data.results.length})</button><button type="button" className={tab==='purchases'?'primaryButton':'ghostButton'} onClick={()=>setTab('purchases')}>Auswahlangebote ({data.offers.length}) · Kauftransaktionen ({data.offers.reduce((s,o)=>s+o.transactions.length,0)})</button><button type="button" className="ghostButton" onClick={()=>void load()} disabled={loading}>Neu laden</button></div>
   {tab==='search'?<>
    <div className="filterRow"><select value={kind} aria-label="Suchtreffer nach Status filtern" onChange={e=>setKind(e.target.value as Kind|'ALL')}>{categories.map(c=><option key={c.key} value={c.key}>{c.label} ({c.key==='ALL'?data.results.length:data.counts[c.key]})</option>)}</select><input aria-label="Treffer suchen" placeholder="Titel, eBay-ID oder Ablehnungsgrund suchen" value={query} onChange={e=>setQuery(e.target.value)}/></div>
    <p style={{fontSize:12,margin:0}}>Angezeigt: {items.length} von {data.results.length} gespeicherten Treffern. Jeder Eintrag kann einzeln bei eBay geöffnet werden.</p>
    <div style={{maxHeight:620,overflowY:'auto',display:'grid',gap:8,paddingRight:4}}>{items.map((item,i)=><div key={`${item.itemId}-${i}`} style={{display:'flex',gap:12,padding:10,border:'1px solid var(--border)',borderRadius:10,alignItems:'flex-start'}}>
      {item.imageUrl&&<a href={item.url||'#'} target="_blank" rel="noopener noreferrer" style={{width:62,flexShrink:0}}><img loading="lazy" referrerPolicy="no-referrer" src={item.imageUrl} alt="eBay-Kartenfoto" style={{width:62,height:85,objectFit:'contain'}}/></a>}
      <div style={{minWidth:0,display:'grid',gap:4,fontSize:13}}><a href={item.url||'#'} target="_blank" rel="noopener noreferrer">{item.title||item.itemId}</a><strong>{kindText[item.kind]}</strong><small>{item.soldDate?`eBay-Verkaufsdatum: ${item.soldDate}`:'Kein Verkaufsdatum'} · {money(item.displayedPrice)} · ID: {item.itemId}</small>{item.collectorExclusions&&<small>Collector-Ausschluss: {item.collectorExclusions.replaceAll(';',', ')}</small>}</div>
     </div>)}</div>
   </>:<>
    <p style={{fontSize:12,margin:0}}>Hier stehen <strong>sämtliche gespeicherten</strong> Auswahlangebots-Referenzen und alle öffentlich auslesbaren Kaufzeilen. Ein Gesamtverkaufszähler ist kein Nachweis für den Verkauf genau dieser Karte.</p>
    <div style={{display:'grid',gap:12}}>{data.offers.map(offer=><div key={offer.itemId} style={{padding:12,border:'1px solid var(--border)',borderRadius:12,display:'grid',gap:7}}>
      <a href={offer.url} target="_blank" rel="noopener noreferrer"><strong>{offer.title}</strong></a>
      <small>eBay-ID {offer.itemId} · Angezeigter Angebotspreis: {money(offer.displayedPrice)} · Kaufübersicht: {offer.purchaseStatus||'Noch nicht geprüft'}</small>
      <strong style={{fontSize:13}}>{offer.transactions.length} öffentlich sichtbare Kaufzeilen</strong>
      {offer.transactions.length?<div style={{display:'grid',gap:5}}>{offer.transactions.map((tx,i)=><div key={i} style={{padding:'6px 0',borderTop:'1px solid var(--border)',fontSize:13}}>{i+1}. {tx.variant} · {tx.displayedPrice} · {tx.quantity}× · {tx.purchasedAt}</div>)}</div>:<small>Keine einzeln auswertbaren Kaufzeilen verfügbar.</small>}
      <a href={`https://www.ebay.de/bin/purchaseHistory?item=${encodeURIComponent(offer.itemId)}`} target="_blank" rel="noopener noreferrer" style={{fontSize:12}}>Original-Kaufübersicht bei eBay prüfen</a>
    </div>)}</div>
   </>}
  </div>}
 </section>;
}
