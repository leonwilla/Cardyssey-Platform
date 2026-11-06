'use client';
import {useCallback,useEffect,useMemo,useState} from 'react';
import {useRouter} from 'next/navigation';
import {AppShell} from '@/components/AppShell';
import {CardReview,type Entry} from '@/components/CardmarketReviewCard';
import {EbayCompactReview} from '@/components/EbayCompactReview';
import {EbayAllSearchEvidence} from '@/components/EbayAllSearchEvidence';
import type {User} from '@/lib/types';

type Scan={language:string;totalVariants:number;uniqueCards:number;browserTotal:number;feedOnly:number;browserProcessed:number;browserRemaining:number;progressPercent:number;status:string;lastCard:string;updatedAt:string|null;problemCountInObserved:number;recentProblems:{cardId:string;variantId:string;status:string;setId:string;detail:string}[];recentEvents:{cardId:string;status:string;at:string}[]};
type Job={id:string;name:string;status:string;done:number;total:number;counts:Record<string,number>;etaSeconds:number|null;running:boolean};
type Jobs={jobs:Job[];collectorActive:boolean;queueActive:boolean};
type ReviewResponse={total:number;items:Entry[]};
type Ebay={cardId:string;setId:string;name:string;number:string;price:number|null;sales:number|null;status:string;failure?:string;reviewRequired?:boolean;reviewReasons?:string[];review?:{status:string;refreshDays:number;showOfferReferences:boolean;note:string};offerReferences?:{title:string;url:string;price:number|null;itemId?:string}[]};
type EbayResponse={items:Ebay[];catalogCounts:Record<string,number>};
const fmt=(n:number)=>n.toLocaleString('de-DE');
const readable=(s:string)=>({RUNNING:'Läuft',COMPLETE:'Fertig',WAITING:'Wartet',QUEUED:'Wartet',INTERRUPTED:'Unterbrochen',PROVIDER_TIMEOUT:'Anbieter antwortet nicht',BLOCKED:'Vom Anbieter pausiert',BATCH_COMPLETE_MORE_PENDING:'Weitere Karten offen',NO_EXACT_NUMBER_SEARCH_HIT:'Karte nicht eindeutig gefunden'} as Record<string,string>)[s]||s.replaceAll('_',' ');
const percent=(n:number,t:number)=>t?Math.min(100,Math.round(n/t*1000)/10):0;
const sets=[{id:'30th',name:'30 Jahre · Jubiläum'},{id:'30th-c',name:'30 Jahre · Classic'},{id:'mep',name:'MEP-Promos'},{id:'sv02',name:'Entwicklungen in Paldea'},{id:'sv01',name:'Karmesin & Purpur'}];
function Progress({done,total}:{done:number;total:number}){return <div role="progressbar" aria-valuenow={done} aria-valuemin={0} aria-valuemax={total||1} style={{height:9,background:'var(--border)',borderRadius:8,overflow:'hidden',marginTop:9}}><div style={{height:'100%',width:`${percent(done,total)}%`,background:'var(--accent,#b98a46)'}}/></div>}
export default function PriceMonitorPage(){
 const router=useRouter();
 const [user,setUser]=useState<User|null>(null);const [scans,setScans]=useState<Record<string,Scan>>({});const [jobs,setJobs]=useState<Jobs|null>(null);
 const [reviews,setReviews]=useState<ReviewResponse>({total:0,items:[]});const [reviewPage,setReviewPage]=useState(0);const [reviewLang,setReviewLang]=useState<'de'|'en'>('de');
 const [reviewSearch,setReviewSearch]=useState('');const [reviewLoading,setReviewLoading]=useState(false);
 const [ebay,setEbay]=useState<Ebay[]>([]);const [ebayCount,setEbayCount]=useState<Record<string,number>>({});const [ebaySearch,setEbaySearch]=useState('');
 const [reviewTab,setReviewTab]=useState<'cardmarket'|'ebay'>('cardmarket');const [expanded,setExpanded]=useState<string|null>(null);
 const [starting,setStarting]=useState<string|null>(null);const [statusError,setStatusError]=useState('');const [reviewError,setReviewError]=useState('');const [ebayError,setEbayError]=useState('');
 const [showHistory,setShowHistory]=useState<string|null>(null);const [showScanErrors,setShowScanErrors]=useState(false);const [selectedIssue,setSelectedIssue]=useState<string|null>(null);const [issueReview,setIssueReview]=useState<Entry|null>(null);const [issueInfo,setIssueInfo]=useState('');
 useEffect(()=>{let mounted=true;fetch('/api/auth/me',{cache:'no-store'}).then(async r=>{if(!r.ok){router.replace('/login');return null}return r.json() as Promise<User>}).then(u=>{if(!u||!mounted)return;if(!u.canAdmin&&u.role!=='ADMIN'&&u.role!=='FOUNDER'){router.replace('/account');return}setUser(u)}).catch(()=>router.replace('/login'));return()=>{mounted=false}},[router]);
 const loadStatuses=useCallback(async()=>{
  const outcomes=await Promise.allSettled([
   fetch('/api/admin/cardmarket-scan?language=de',{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error('Cardmarket DE');return r.json() as Promise<Scan>}),
   fetch('/api/admin/cardmarket-scan?language=en',{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error('Cardmarket EN');return r.json() as Promise<Scan>}),
   fetch('/api/admin/price-jobs-overview',{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error('eBay Jobs');return r.json() as Promise<Jobs>})]);
  const fresh:Record<string,Scan>={};if(outcomes[0].status==='fulfilled')fresh.de=outcomes[0].value;
  if(outcomes[1].status==='fulfilled')fresh.en=outcomes[1].value;
  setScans(old=>({...old,...fresh}));if(outcomes[2].status==='fulfilled')setJobs(outcomes[2].value);
  setStatusError(outcomes.every(x=>x.status==='fulfilled')?'':'Einige Scan-Statusmeldungen sind gerade nicht erreichbar. Die letzten Werte bleiben sichtbar.');
 },[]);
 const loadReviews=useCallback(async()=>{
  setReviewLoading(true);
  try{const q=new URLSearchParams({language:reviewLang,status:'PENDING_REVIEW',search:reviewSearch,page:String(reviewPage)});
   const r=await fetch('/api/admin/cardmarket-print-review?'+q,{cache:'no-store'});if(!r.ok)throw Error('Prüffälle nicht erreichbar');
   const data=await r.json() as ReviewResponse;setReviews(data);setReviewError('')
  }catch(e){setReviewError(e instanceof Error?e.message:'Fehler beim Laden')}finally{setReviewLoading(false)}
 },[reviewLang,reviewSearch,reviewPage]);
 const loadEbay=useCallback(async()=>{try{const r=await fetch('/api/admin/price-sets',{cache:'no-store'});if(!r.ok)throw Error();const data=await r.json() as EbayResponse;setEbay(data.items||[]);setEbayCount(data.catalogCounts||{});setEbayError('')}catch{setEbayError('eBay-Prüfungen vorübergehend nicht erreichbar')}},[]);
 useEffect(()=>{const p=new URLSearchParams(window.location.search);if(p.get('review')==='ebay')setReviewTab('ebay');const search=p.get('search');if(search)setReviewSearch(search)},[]);
 useEffect(()=>{if(!user)return;void loadStatuses();const t=setInterval(()=>void loadStatuses(),15000);return()=>clearInterval(t)},[user,loadStatuses]);
 useEffect(()=>{if(!user)return;void loadReviews()},[user,loadReviews]);
 useEffect(()=>{if(!user)return;void loadEbay()},[user,loadEbay]);
 async function openIssue(language:'de'|'en',cardId:string,variantId:string){
  const key=language+'|'+cardId+'|'+variantId;
  if(selectedIssue===key){setSelectedIssue(null);setIssueReview(null);return}
  setSelectedIssue(key);setIssueReview(null);setIssueInfo('');
  try{
   const q=new URLSearchParams({language,status:'PENDING_REVIEW',search:cardId,page:'0'});
   const r=await fetch('/api/admin/cardmarket-print-review?'+q,{cache:'no-store'});if(!r.ok)throw Error();
   const data=await r.json() as ReviewResponse;
   const matched=data.items.find(x=>x.card_id===cardId&&x.variant_id===variantId);
   if(matched)setIssueReview(matched);else setIssueInfo('Für diese Variante liegt noch kein bearbeitbarer Kartenprüffall vor. Ein technischer Scanfehler wird automatisch erneut versucht; bitte keine unbestätigte ID eintragen.');
  }catch{setIssueInfo('Die Kartenzuordnung konnte nicht geladen werden.')}
 }
 async function startSet(id:string){setStarting(id);setStatusError('');try{const r=await fetch('/api/admin/price-set-jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({setId:id})});const data=await r.json();if(!r.ok)throw Error(data.error==='EBAY_BROWSER_BUSY'?'Der eBay-Browser arbeitet bereits.':'Set-Scan konnte nicht gestartet werden.');await loadStatuses()}catch(e){setStatusError(e instanceof Error?e.message:'Start fehlgeschlagen')}finally{setStarting(null)}}
 const openEbay=useMemo(()=>ebay.filter(e=>e.reviewRequired).filter(e=>[e.name,e.number,e.cardId,e.setId].join(' ').toLowerCase().includes(ebaySearch.toLowerCase())),[ebay,ebaySearch]);
 return <AppShell active="/admin/prices" user={user}>
  <section className="pageIntro"><div><span className="eyebrowText">Admin · Scan-Zentrale</span><h1>Scans & offene Prüfungen</h1><p>Alle laufenden Preisabfragen an einem Ort. Oben der Fortschritt, unten ausschließlich Fälle, die deine Entscheidung brauchen.</p></div></section>
  <div className="filterRow" style={{justifyContent:'flex-end',gap:10,marginBottom:16}}><small>Scan-Status automatisch alle 15 Sekunden</small><button className="ghostButton" onClick={()=>{void loadStatuses();void loadReviews();void loadEbay()}}>Alles aktualisieren</button></div>
  <section className="sectionBlock" aria-label="Scanaufträge" style={{marginBottom:28}}>
   <div className="sectionTitle"><div><span className="eyebrowText">01 · Automatische Scripts</span><h2>Scan-Fortschritt</h2></div></div>
   {statusError&&<p role="alert">{statusError}</p>}
   <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,290px),1fr))',gap:12}}>
    {(['de','en'] as const).map(lang=>{const s=scans[lang];return <article className="statusPanel" key={lang} style={{padding:18,display:'grid',gap:10}}><div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:8}}><strong>Cardmarket · {lang==='de'?'Deutsch':'Englisch'}</strong><small>{lang==='en'&&(scans.de?.browserRemaining||0)>0?'Wartet auf Deutsch':s?readable(s.status):'Lädt …'}</small></div>{s?<><div><strong style={{fontSize:23}}>{fmt(s.browserProcessed)} / {fmt(s.browserTotal)}</strong><div style={{fontSize:12,opacity:.75}}>Browser-Prüfungen · {percent(s.browserProcessed,s.browserTotal)} %</div><Progress done={s.browserProcessed} total={s.browserTotal}/></div><div style={{fontSize:12}}>{fmt(s.uniqueCards)} Karten · {fmt(s.totalVariants)} Varianten insgesamt<br/>{fmt(s.feedOnly)} Varianten über Preisfeeds, nicht browsergescannt</div><div style={{fontSize:12,opacity:.8}}>Letzte Karte: {s.lastCard||'—'}<br/>Stand: {s.updatedAt?new Date(s.updatedAt).toLocaleString('de-DE'):'Nicht gestartet'}</div>{s.problemCountInObserved>0&&<button className="ghostButton" onClick={()=>{setReviewTab('cardmarket');setReviewLang(lang);setReviewPage(0);document.getElementById('offene-pruefungen')?.scrollIntoView({behavior:'smooth'})}}>{fmt(s.problemCountInObserved)} Scan-Hinweise ansehen</button>}{showHistory===lang&&<div style={{borderTop:'1px solid var(--border)',paddingTop:8,fontSize:12}}>{s.recentEvents.map((x,i)=><p key={i}>{x.at?new Date(x.at).toLocaleString('de-DE'):''} · {x.cardId} · {readable(x.status)}</p>)}</div>}<button className="ghostButton" onClick={()=>setShowHistory(v=>v===lang?null:lang)}>{showHistory===lang?'Verlauf schließen':'Letzte Scan-Schritte'}</button></>:<p>Keine Scandaten verfügbar.</p>}</article>})}
   </div>
   <div style={{marginTop:14,display:'grid',gap:10}}><h3>eBay · Verkaufspreise</h3><p style={{fontSize:13,opacity:.75}}>Nur seltene und besondere Karten. Preise aus bestätigten Verkäufen, keine Bulk-Angebote.</p>{sets.map(set=>{const job=jobs?.jobs.find(x=>x.id===set.id);const n=ebay.filter(x=>x.setId===set.id);return <div className="statusPanel" key={set.id} style={{padding:14,display:'grid',gap:8}}><div style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:12,flexWrap:'wrap'}}><div><strong>{set.name}</strong><div style={{fontSize:12,opacity:.75}}>{job?readable(job.status):'Kein aktiver Scan'} · {fmt(n.filter(x=>x.price!=null).length)} Preise / {fmt(ebayCount[set.id]||0)} Zielkarten</div></div><button className="ghostButton" disabled={starting!==null||job?.running===true||jobs?.collectorActive===true} onClick={()=>void startSet(set.id)}>{starting===set.id?'Startet …':job?.running?'Läuft …':'Set-Scan starten'}</button></div>{job&&job.total>0&&<><div style={{fontSize:12}}>{fmt(job.done)} / {fmt(job.total)} geprüft · {percent(job.done,job.total)} %</div><Progress done={job.done} total={job.total}/></>}</div>})}</div>
  </section>
  <section className="sectionBlock" id="offene-pruefungen" aria-label="Offene Kartenprüfungen"><div className="sectionTitle"><div><span className="eyebrowText">02 · Deine Entscheidungen</span><h2>Offene Prüfungen</h2></div></div>
   <div className="statusPanel" style={{padding:14,marginBottom:16}}><div style={{display:'flex',gap:12,justifyContent:'space-between',alignItems:'center',flexWrap:'wrap'}}><div><strong>Scan-Hinweise</strong><div style={{fontSize:12,opacity:.75}}>{(['de','en'] as const).reduce((n,k)=>n+(scans[k]?.problemCountInObserved||0),0)} bisher erkannte Hinweise aus DE/EN · technische Fehler werden beim nächsten Scan erneut geprüft</div></div><button className="ghostButton" onClick={()=>setShowScanErrors(v=>!v)}>{showScanErrors?'Ausblenden':'Letzte Hinweise ansehen'}</button></div>
   {showScanErrors&&<div style={{display:'grid',gap:9,marginTop:14}}>{(['de','en'] as const).flatMap(lang=>(scans[lang]?.recentProblems||[]).map(p=>({...p,language:lang}))).map(p=><div key={p.language+'|'+p.cardId+'|'+p.variantId} style={{borderTop:'1px solid var(--border)',paddingTop:10,display:'grid',gap:8}}><div style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:12,flexWrap:'wrap'}}><div><strong>{p.language.toUpperCase()} · {p.cardId}</strong> <small>({p.setId})</small><div style={{fontSize:12}}>{readable(p.status)} {p.detail}</div></div><button className="ghostButton" onClick={()=>void openIssue(p.language,p.cardId,p.variantId)}>{selectedIssue===p.language+'|'+p.cardId+'|'+p.variantId?'Schließen':'Zuordnung prüfen'}</button></div>{selectedIssue===p.language+'|'+p.cardId+'|'+p.variantId&&(issueReview?<CardReview entry={issueReview} onSaved={()=>{setSelectedIssue(null);setIssueReview(null);void loadReviews()}}/>:<small>{issueInfo||'Wird geladen …'}</small>)}</div>)}</div>}
   </div>
   <div className="filterRow" style={{gap:10,marginBottom:16}}><button className={reviewTab==='cardmarket'?'primaryButton':'ghostButton'} onClick={()=>setReviewTab('cardmarket')}>Cardmarket · Zuordnung</button><button className={reviewTab==='ebay'?'primaryButton':'ghostButton'} onClick={()=>setReviewTab('ebay')}>eBay · Angebote {ebay.filter(x=>x.reviewRequired).length>0?'('+fmt(ebay.filter(x=>x.reviewRequired).length)+')':''}</button></div>
   {reviewTab==='cardmarket'?<><div className="filterRow" style={{gap:10,marginBottom:14}}><select aria-label="Sprache" value={reviewLang} onChange={e=>{setReviewLang(e.target.value as 'de'|'en');setReviewPage(0)}}><option value="de">Deutsch</option><option value="en">Englisch</option></select><input aria-label="Prüffälle durchsuchen" placeholder="Karte, Set oder Nummer suchen" value={reviewSearch} onChange={e=>{setReviewSearch(e.target.value);setReviewPage(0)}}/><button className="ghostButton" onClick={()=>void loadReviews()}>Aktualisieren</button></div>{reviewError&&<p role="alert">{reviewError}</p>}<p style={{fontSize:13,marginBottom:12}}>{fmt(reviews.total)} offene Zuordnungen · Seite {reviewPage+1}{reviewLoading?' · lädt …':''}</p><div style={{display:'grid',gap:12}}>{reviews.items.map(entry=><CardReview key={entry.card_id+entry.variant_id} entry={entry} onSaved={()=>void loadReviews()}/>)}</div>{!reviews.items.length&&!reviewLoading&&<p>Keine offenen Fälle für diesen Filter.</p>}<div className="filterRow" style={{gap:10,marginTop:16}}><button className="ghostButton" disabled={reviewPage===0} onClick={()=>setReviewPage(p=>p-1)}>← Zurück</button><button className="ghostButton" disabled={(reviewPage+1)*50>=reviews.total} onClick={()=>setReviewPage(p=>p+1)}>Nächste 50 →</button></div></>:<><div className="filterRow" style={{marginBottom:14}}><input aria-label="eBay Fälle suchen" placeholder="Karte, Nummer oder Set suchen" value={ebaySearch} onChange={e=>setEbaySearch(e.target.value)}/><button className="ghostButton" onClick={()=>void loadEbay()}>Aktualisieren</button></div>{ebayError&&<p role="alert">{ebayError}</p>}<p style={{fontSize:13,marginBottom:12}}>{fmt(openEbay.length)} offene eBay-Prüfungen</p><div style={{display:'grid',gap:10}}>{openEbay.map(e=><article key={e.cardId} className="statusPanel" style={{padding:15}}><div style={{display:'flex',justifyContent:'space-between',gap:10,flexWrap:'wrap',alignItems:'center'}}><div><strong>{e.name} · {e.number}</strong><div style={{fontSize:12,opacity:.75}}>{e.setId} · {e.reviewReasons?.join(' · ')||readable(e.status)}</div></div><button className="ghostButton" onClick={()=>setExpanded(v=>v===e.cardId?null:e.cardId)}>{expanded===e.cardId?'Schließen':'Angebote prüfen'}</button></div>{expanded===e.cardId&&<div style={{marginTop:14,borderTop:'1px solid var(--border)',paddingTop:12}}><EbayAllSearchEvidence cardId={e.cardId}/><EbayCompactReview cardId={e.cardId} review={e.review} onSaved={()=>{setExpanded(null);void loadEbay()}}/></div>}</article>)}</div>{!openEbay.length&&<p>Keine offenen eBay-Prüfungen.</p>}</>}
  </section>
 </AppShell>;
}
