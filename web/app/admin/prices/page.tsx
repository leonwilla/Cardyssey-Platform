'use client';
import {useCallback,useEffect,useMemo,useState} from 'react';
import {useRouter} from 'next/navigation';
import {AppShell} from '@/components/AppShell';
import {CardReview,type Entry} from '@/components/CardmarketReviewCard';
import {EbayCompactReview} from '@/components/EbayCompactReview';
import {EbayAllSearchEvidence} from '@/components/EbayAllSearchEvidence';
import {CardmarketIndexPanel,type IndexSnapshot} from '@/components/CardmarketIndexPanel';
import {EbaySoldPanel,type EbaySoldSnapshot} from '@/components/EbaySoldPanel';
import './admin-prices.css';
import type {User} from '@/lib/types';

type Scan={language:string;collectorProcessed?:number|null;collectorTotal?:number|null;collectorUpdatedAt?:string|null;statusSnapshotAt?:string|null;localCooldownActive?:boolean;localNextAllowedAt?:string|null;cooldownBlockingLanguage?:string|null;cooldownBlockingStatus?:string|null;cooldownMinutes?:number|null;blockedStreak?:number|null;sessionCheckAgeSeconds?:number|null;lastIncident?:{at?:string|null;cardId?:string|null;title?:string|null;path?:string|null;kind?:string|null;stage?:string|null;httpStatus?:number|null;signal?:string|null}|null;rescanStartedAt?:string|null;rescanProcessed?:number|null;nextAllowedAt?:string|null;cooldownActive?:boolean;secondsUntilAllowed?:number;currentCycleObserved?:number;currentCycleIssues?:number;lastObservedAt?:string|null;lastResultStatus?:string;lastVariant?:string;totalVariants:number;uniqueCards:number;browserTotal:number;feedOnly:number;deltaBrowserSkips?:number;deltaPreviewSkips?:number;deltaPreviewStatus?:string|null;deltaPreviewGuideAt?:string|null;browserProcessed:number;productMapped:number;noExactSearchMatch:number;pricedVariants:number;missingVariants:number;browserMissingPriority:number;feedMissingPriority:number;browserRemaining:number;progressPercent:number;status:string;lastCard:string;updatedAt:string|null;problemCountInObserved:number;problemCountCurrentCycle?:number;missingFilterInputs?:number;nonfilterableSpecialPrints?:number;recentProblems:{cardId:string;variantId:string;status:string;setId:string;detail:string}[];recentEvents:{cardId:string;status:string;at:string}[];browserSession?:{status:string;reason:string;login:string;checkedAt:string;profileExists:boolean}};
type Job={id:string;name:string;status:string;done:number;total:number;counts:Record<string,number>;etaSeconds:number|null;running:boolean};
type Jobs={jobs:Job[];collectorActive:boolean;queueActive:boolean};
type ReviewResponse={total:number;allPending?:number;items:Entry[];recheck?:{mode:string;lastAuditedAt:string|null;manualCandidates:number|null;automaticallyQueued:number|null}};
type Ebay={cardId:string;setId:string;name:string;number:string;price:number|null;sales:number|null;status:string;failure?:string;reviewRequired?:boolean;reviewReasons?:string[];review?:{status:string;refreshDays:number;showOfferReferences:boolean;note:string};offerReferences?:{title:string;url:string;price:number|null;itemId?:string}[]};
type EbayResponse={items:Ebay[];catalogCounts:Record<string,number>};
type ScanFailure={specialPrintComments?:{target:string;counts:{positive:number;shorthand_hint?:number;contradiction:number;ambiguous:number;missing:number;not_applicable:number;comment_fields_visible:number};not_print_proof:boolean}|null;scoreMatchState?:string;scorePageCandidateOnly?:boolean;scoreCandidateUrls?:string[];filterMode?:string;officialProductGuide?:{trend?:number|null;trend_holo?:number|null;avg30?:number|null;avg30_holo?:number|null;guide_date?:string;can_publish_language_print_price?:false}|null;printStamp?:string;printFoil?:string;referenceUrl?:string;missingFields?:string[];unfilterablePrintFeatures?:string[];cardId:string;variantId:string;setId:string;name:string;language:'de'|'en';status:string;type:'TECHNISCH'|'ZUORDNUNG'|'DATEN_FEHLEN'|'PREISPRUEFUNG'|'DRUCKPRUEFUNG'|'ID_VERKNUEPFT_STEMPEL';detail:string;seenAt:string;productId:string};
type ScanFailures={total:number;technical:number;assignment:number;missingData?:number;priceChecks?:number;printChecks?:number;linkedStamps?:number;page:number;items:ScanFailure[]};
const fmt=(n:number)=>n.toLocaleString('de-DE');
const providerStageLabel:Record<string,string>={
 SEARCH_FETCH:'Suchanfrage',
 SEARCH_PAGE:'Suchseite',
 PRODUCT_FETCH:'Produktanfrage',
 PRODUCT_PAGE:'Produktseite',
 DIRECT_ID_INTERSTITIAL:'Produkt-ID-Weiterleitung',
 SESSION_BOOTSTRAP:'Browserstart',
};
const readable=(s:string)=>({RUNNING:'Läuft',COMPLETE:'Fertig',WAITING:'Wartet',QUEUED:'Wartet',INTERRUPTED:'Unterbrochen',PROVIDER_TIMEOUT:'Anbieter antwortet nicht',BLOCKED:'Scan pausiert: Anbieterblock',LOGIN_REQUIRED:'Scan pausiert: Anmeldung fehlt',LOGIN_UNVERIFIED:'Scan pausiert: Anmeldung nicht bestätigt',BATCH_COMPLETE_MORE_PENDING:'Weitere Karten offen',NO_EXACT_NUMBER_SEARCH_HIT:'Karte nicht eindeutig gefunden'} as Record<string,string>)[s]||s.replaceAll('_',' ');
const percent=(n:number,t:number)=>t?Math.min(100,Math.round(n/t*1000)/10):0;
const sets=[{id:'30th',name:'30 Jahre · Jubiläum'},{id:'30th-c',name:'30 Jahre · Classic'},{id:'mep',name:'MEP-Promos'},{id:'sv02',name:'Entwicklungen in Paldea'},{id:'sv01',name:'Karmesin & Purpur'}];
function Progress({done,total}:{done:number;total:number}){return <div className="ap-bar" role="progressbar" aria-valuenow={done} aria-valuemin={0} aria-valuemax={total||1}><i style={{width:`${percent(done,total)}%`}}/></div>}
type Tab='scanner'|'sets'|'pruefungen'|'ebay';
const typeColor:Record<string,string>={ZUORDNUNG:'var(--ap-warn)',DRUCKPRUEFUNG:'#7a5cc4',ID_VERKNUEPFT_STEMPEL:'#3c7fb5',PREISPRUEFUNG:'var(--ap-ok)',TECHNISCH:'var(--ap-bad)',DATEN_FEHLEN:'var(--ap-idle)'};
const typeLabel:Record<string,string>={ZUORDNUNG:'Zuordnung',DRUCKPRUEFUNG:'Sonderdruck',ID_VERKNUEPFT_STEMPEL:'Stempel',PREISPRUEFUNG:'Preisabfrage',TECHNISCH:'Technik',DATEN_FEHLEN:'Daten fehlen'};
const eur=(v?:number|null)=>v!=null?v.toLocaleString('de-DE',{style:'currency',currency:'EUR'}):'–';
/** Status of one language scan as energy mark: colour class + short label. */
function scanState(s:Scan|undefined,lang:string):[string,string]{
 if(!s)return ['ap-idle','Lädt …'];
 if(s.status==='RUNNING')return ['ap-ok','Scan läuft'];
 if(s.status==='RUNNING_STALLED')return ['ap-bad','Kein Fortschritt'];
 if(s.browserSession?.status==='BLOCKED'||s.cooldownBlockingStatus==='BLOCKED')return ['ap-bad','Cloudflare-Box'];
 if(s.localCooldownActive)return ['ap-warn','Pause '+lang.toUpperCase()];
 if(s.cooldownActive)return ['ap-warn','Wartet auf '+(s.cooldownBlockingLanguage||'').toUpperCase()];
 if(s.status==='BATCH_COMPLETE_MORE_PENDING')return ['ap-ok','Nächster Lauf geplant'];
 return ['ap-idle',readable(s.status)];
}
export default function PriceMonitorPage(){
 const router=useRouter();
 const [user,setUser]=useState<User|null>(null);const [scans,setScans]=useState<Record<string,Scan>>({});const [jobs,setJobs]=useState<Jobs|null>(null);
 const [reviews,setReviews]=useState<ReviewResponse>({total:0,items:[]});const [reviewPage,setReviewPage]=useState(0);const [reviewLang,setReviewLang]=useState<'de'|'en'>('de');
 const [reviewStatus,setReviewStatus]=useState<'PENDING_REVIEW'|'CONFIRMED_PRINT'|'NO_MATCH'|'DEFERRED'>('PENDING_REVIEW');const [reviewSearch,setReviewSearch]=useState('');const [showAllCandidateCases,setShowAllCandidateCases]=useState(false);const [reviewLoading,setReviewLoading]=useState(false);
 const [ebay,setEbay]=useState<Ebay[]>([]);const [ebayCount,setEbayCount]=useState<Record<string,number>>({});const [ebaySearch,setEbaySearch]=useState('');
 const [reviewTab,setReviewTab]=useState<'cardmarket'|'ebay'>('cardmarket');const [expanded,setExpanded]=useState<string|null>(null);
 const [cardmarketResuming,setCardmarketResuming]=useState(false);const [cardmarketResetting,setCardmarketResetting]=useState(false);const [cardmarketResumeMessage,setCardmarketResumeMessage]=useState('');const [starting,setStarting]=useState<string|null>(null);const [statusError,setStatusError]=useState('');const [reviewError,setReviewError]=useState('');const [ebayError,setEbayError]=useState('');
 const [failures,setFailures]=useState<ScanFailures>({total:0,technical:0,assignment:0,page:0,items:[]});const [failureLang,setFailureLang]=useState<'de'|'en'>('de');const [failureKind,setFailureKind]=useState<'karten'|'preise'|'technik'|'drucke'|'verknuepft'|'alle'>('karten');const [failureScope,setFailureScope]=useState<'current'|'all'>('current');const [failurePage,setFailurePage]=useState(0);const [failureSearch,setFailureSearch]=useState('');const [failureError,setFailureError]=useState('');const [retryingFailure,setRetryingFailure]=useState<string|null>(null);const [retryFeedback,setRetryFeedback]=useState('');const [showHistory,setShowHistory]=useState<string|null>(null);const [showScanErrors,setShowScanErrors]=useState(true);const [selectedIssue,setSelectedIssue]=useState<string|null>(null);const [issueReview,setIssueReview]=useState<Entry|null>(null);const [issueInfo,setIssueInfo]=useState('');
 const [exportingFailureLang,setExportingFailureLang]=useState<'de'|'en'|null>(null);
 const [failureExportError,setFailureExportError]=useState('');
 const [tab,setTab]=useState<Tab>('scanner');const [reviewArea,setReviewArea]=useState<'fehler'|'zuordnung'>('fehler');
 const [index,setIndex]=useState<IndexSnapshot|null>(null);const [indexError,setIndexError]=useState('');
 const [ebaySold,setEbaySold]=useState<EbaySoldSnapshot|null>(null);const [ebaySoldError,setEbaySoldError]=useState('');
 const loadEbaySold=useCallback(async()=>{try{const r=await fetch('/api/admin/ebay-sold',{cache:'no-store'});if(!r.ok)throw Error();setEbaySold(await r.json() as EbaySoldSnapshot);setEbaySoldError('')}catch{setEbaySoldError('Status des eBay-Verkaufsscanners gerade nicht erreichbar')}},[]);
 const loadIndex=useCallback(async()=>{try{const r=await fetch('/api/admin/cardmarket-index',{cache:'no-store'});if(!r.ok)throw Error();setIndex(await r.json() as IndexSnapshot);setIndexError('')}catch{setIndexError('Status des Set-Listen-Scans gerade nicht erreichbar')}},[]);
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
  try{const q=new URLSearchParams({language:reviewLang,status:reviewStatus,search:reviewSearch,page:String(reviewPage),mode:reviewStatus!=='PENDING_REVIEW'||showAllCandidateCases||reviewSearch.trim()?'all':'manual'});
   const r=await fetch('/api/admin/cardmarket-print-review?'+q,{cache:'no-store'});if(!r.ok)throw Error('Prüffälle nicht erreichbar');
   const data=await r.json() as ReviewResponse;setReviews(data);setReviewError('')
  }catch(e){setReviewError(e instanceof Error?e.message:'Fehler beim Laden')}finally{setReviewLoading(false)}
 },[reviewLang,reviewStatus,reviewSearch,reviewPage,showAllCandidateCases]);
 const loadFailures=useCallback(async()=>{
  try{const q=new URLSearchParams({language:failureLang,scope:failureScope,kind:failureKind,page:String(failurePage),search:failureSearch});const r=await fetch('/api/admin/cardmarket-scan-failures?'+q,{cache:'no-store'});if(!r.ok)throw Error('Scanfehlerliste nicht erreichbar');setFailures(await r.json() as ScanFailures);setFailureError('')}catch(e){setFailureError(e instanceof Error?e.message:'Scanfehlerliste nicht erreichbar')}
 },[failureLang,failureScope,failureKind,failurePage,failureSearch]);
 const loadEbay=useCallback(async()=>{try{const r=await fetch('/api/admin/price-sets',{cache:'no-store'});if(!r.ok)throw Error();const data=await r.json() as EbayResponse;setEbay(data.items||[]);setEbayCount(data.catalogCounts||{});setEbayError('')}catch{setEbayError('eBay-Prüfungen vorübergehend nicht erreichbar')}},[]);
 useEffect(()=>{const p=new URLSearchParams(window.location.search);const t=p.get('tab');if(t==='scanner'||t==='sets'||t==='pruefungen'||t==='ebay')setTab(t);if(p.get('review')==='ebay'){setReviewTab('ebay');setTab('ebay')}const search=p.get('search');if(search){setReviewSearch(search);setTab('pruefungen');setReviewArea('zuordnung')}},[]);
 useEffect(()=>{if(!user)return;void loadStatuses();const t=setInterval(()=>void loadStatuses(),15000);return()=>clearInterval(t)},[user,loadStatuses]);
 useEffect(()=>{if(!user)return;void loadReviews();const t=setInterval(()=>void loadReviews(),30000);return()=>clearInterval(t)},[user,loadReviews]);
 useEffect(()=>{if(!user)return;void loadEbay()},[user,loadEbay]);
 useEffect(()=>{if(!user)return;void loadIndex();const t=setInterval(()=>void loadIndex(),60000);return()=>clearInterval(t)},[user,loadIndex]);
 useEffect(()=>{if(!user||tab!=='ebay')return;void loadEbaySold();const t=setInterval(()=>void loadEbaySold(),60000);return()=>clearInterval(t)},[user,tab,loadEbaySold]);
 useEffect(()=>{if(!user||!showScanErrors)return;void loadFailures();const t=setInterval(()=>void loadFailures(),15000);return()=>clearInterval(t)},[user,showScanErrors,loadFailures]);
 async function exportFailures(language:'de'|'en'){
  setExportingFailureLang(language);
  setFailureExportError('');
  try{
   const params=new URLSearchParams({language,scope:failureScope,kind:failureKind,search:failureSearch,format:'csv'});
   const response=await fetch('/api/admin/cardmarket-scan-failures?'+params,{cache:'no-store'});
   if(!response.ok||!response.headers.get('content-type')?.startsWith('text/csv'))throw Error();
   const file=await response.blob();
   const url=URL.createObjectURL(file);
   const download=document.createElement('a');
   download.href=url;
   download.download=response.headers.get('content-disposition')?.match(/filename="([^"]+)"/)?.[1]||'offene-pruefungen-'+language+'.csv';
   document.body.appendChild(download);
   download.click();
   download.remove();
   window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch{
   setFailureExportError('Der CSV-Export konnte nicht geladen werden. Bitte versuche es erneut.');
  }finally{
   setExportingFailureLang(null);
  }
 }
 async function openIssue(language:'de'|'en',cardId:string,variantId:string){
  const key=language+'|'+cardId+'|'+variantId;
  if(selectedIssue===key){setSelectedIssue(null);setIssueReview(null);return}
  setSelectedIssue(key);setIssueReview(null);setIssueInfo('');
  try{
   const q=new URLSearchParams({language,status:'PENDING_REVIEW',search:'card:'+cardId,page:'0',mode:'all'});
   const r=await fetch('/api/admin/cardmarket-print-review?'+q,{cache:'no-store'});if(!r.ok)throw Error();
   const data=await r.json() as ReviewResponse;
   const matched=data.items.find(x=>x.card_id===cardId&&x.variant_id===variantId);
   if(matched)setIssueReview(matched);else setIssueInfo('Für diese Variante liegt noch kein bearbeitbarer Kartenprüffall vor. Ein technischer Scanfehler wird automatisch erneut versucht; bitte keine unbestätigte ID eintragen.');
  }catch{setIssueInfo('Die Kartenzuordnung konnte nicht geladen werden.')}
 }
 async function resumeCardmarket(){setCardmarketResuming(true);setCardmarketResumeMessage('');try{const r=await fetch('/api/admin/cardmarket-scan-control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'resume'})});const d=await r.json();if(!r.ok)throw Error(d.error==='challenge_active'?'Cloudflare-Prüfung aktiv. Bitte in Edge bestätigen.':d.error==='cooldown_active'?'Provider-Schutzpause noch aktiv. Frühester neuer Versuch: '+(d.nextAllowedAt?new Date(d.nextAllowedAt).toLocaleString('de-DE'):'nach Ablauf der Schutzpause'):d.error||'Neustart nicht möglich');setCardmarketResumeMessage('Neustart angefordert. Die Verfügbarkeit wird erneut geprüft; eine Anmeldung ist bei vollständigen öffentlichen Angebotsseiten nicht nötig.');await loadStatuses()}catch(e){setCardmarketResumeMessage(e instanceof Error?e.message:'Neustart fehlgeschlagen')}finally{setCardmarketResuming(false)}}
 async function resetCardmarketScan(){
  if(!window.confirm('Neuen vollständigen Cardmarket-Prüfzyklus ab 0 starten? Deutsch und Englisch werden erneut eingeplant. Bisherige Prüfergebnisse, bestätigte Zuordnungen und Preise bleiben erhalten.'))return;
  setCardmarketResetting(true);setCardmarketResumeMessage('');
  try{
   const r=await fetch('/api/admin/cardmarket-scan-control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'rescan'})});
   const d=await r.json();if(!r.ok)throw Error(d.error==='scan_already_running'?'Laufender Scan konnte nicht kontrolliert beendet werden.':d.error||'Neuscan konnte nicht gestartet werden');
   setCardmarketResumeMessage('Neuer vollständiger Prüfzyklus ab 0 / 31.441 (DE) und 0 / 34.206 (EN) eingeplant. Der Browser startet nur bei bestätigter Anmeldung.');
   await loadStatuses();
  }catch(e){setCardmarketResumeMessage(e instanceof Error?e.message:'Neuscan fehlgeschlagen')}
  finally{setCardmarketResetting(false)}
 }
 async function retryFailedCard(entry:ScanFailure){
  const key=entry.language+'|'+entry.cardId+'|'+entry.variantId;setRetryingFailure(key);setRetryFeedback('');
  try{const r=await fetch('/api/admin/cardmarket-scan-control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'retry',language:entry.language,cardId:entry.cardId,variantId:entry.variantId})});const d=await r.json();if(!r.ok)throw Error(d.error==='card_variant_not_in_current_queue'?'Dieser alte Prüffall hat keine eindeutige Varianten-ID in der aktuellen Warteschlange.':'Erneuter Scan konnte nicht eingeplant werden.');setRetryFeedback(entry.cardId+' wurde für den nächsten Scan priorisiert.');void loadFailures()}
  catch(e){setRetryFeedback(e instanceof Error?e.message:'Erneuter Scan fehlgeschlagen')}
  finally{setRetryingFailure(null)}
 }
 async function startSet(id:string){setStarting(id);setStatusError('');try{const r=await fetch('/api/admin/price-set-jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({setId:id})});const data=await r.json();if(!r.ok)throw Error(data.error==='EBAY_BROWSER_BUSY'?'Der eBay-Browser arbeitet bereits.':'Set-Scan konnte nicht gestartet werden.');await loadStatuses()}catch(e){setStatusError(e instanceof Error?e.message:'Start fehlgeschlagen')}finally{setStarting(null)}}
 const openEbay=useMemo(()=>ebay.filter(e=>e.reviewRequired).filter(e=>[e.name,e.number,e.cardId,e.setId].join(' ').toLowerCase().includes(ebaySearch.toLowerCase())),[ebay,ebaySearch]);
 const de=scans.de,en=scans.en;
 const cfWaiting=index?.clearance.waitingSince;
 const anyRunning=de?.status==='RUNNING'||en?.status==='RUNNING';
 const deckState:[string,string]=cfWaiting||de?.browserSession?.status==='BLOCKED'?['ap-bad','Cloudflare-Box wartet']:anyRunning?['ap-ok','Scanner läuft']:de?.cooldownActive||en?.cooldownActive?['ap-warn','Kurze Pause']:['ap-idle',de?readable(de.status):'Lädt …'];
 const openCases=(de?.problemCountCurrentCycle??de?.problemCountInObserved??0)+(en?.problemCountCurrentCycle??en?.problemCountInObserved??0);
 const factor=index&&index.baseline.pricesPerHour?Math.round(index.speed.pricesPerHour/index.baseline.pricesPerHour):0;
 const progressOf=(s?:Scan)=>[s?.collectorProcessed??s?.browserProcessed??0,s?.collectorTotal??s?.browserTotal??0] as const;
 const ebayOpen=ebay.filter(x=>x.reviewRequired).length;
 const session=de?.browserSession;
 const goToCases=(lang:'de'|'en')=>{setShowScanErrors(true);setFailureLang(lang);setFailureScope('current');setFailurePage(0);setReviewArea('fehler');setTab('pruefungen');document.getElementById('ap-tabs')?.scrollIntoView({behavior:'smooth'})};
 return <AppShell active="/admin/prices" user={user}>
 <div className="ap">
  <header className="ap-deck">
   <div className="ap-deckTop">
    <div><span className="ap-eyebrow">Admin · Scan-Zentrale</span><h1 className="ap-title">Preis-Kommandodeck</h1><p className="ap-sub">Was der Scanner gerade macht, wie schnell er ist und welche Karten deine Entscheidung brauchen.</p></div>
    <div className="ap-live"><span className="ap-livePill"><span className="ap-pulse"/>Live · alle 15 s</span><button type="button" className="ap-deckButton" onClick={()=>{void loadStatuses();void loadReviews();void loadEbay();void loadIndex()}}>Alles aktualisieren</button></div>
   </div>
   <div className="ap-hand">
    <div className="ap-tcard"><div className="ap-tcardHead">Status<span className="ap-tcardNo">#01</span></div><span className={'ap-energy '+deckState[0]} style={{justifySelf:'start'}}>{deckState[1]}</span><div className="ap-tcardFoot">{cfWaiting?'seit '+new Date(cfWaiting).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'})+' · in Edge F5 + Kästchen':session?.login==='AUTHENTICATED'?'Cardmarket eingeloggt':session?.login==='LOGIN_REQUIRED'?'Gastmodus':'Login ungeklärt'}</div></div>
    <div className="ap-tcard"><div className="ap-tcardHead">Preise / Stunde<span className="ap-tcardNo">#02</span></div><div className="ap-tcardValue">{index?index.speed.pricesPerHour.toLocaleString('de-DE'):'–'}</div><div className="ap-tcardFoot">{index?`${index.speed.pagesPerHour.toLocaleString('de-DE')} Seiten/h`+(factor>1?` · ${factor}× schneller als früher`:''):'lädt …'}</div></div>
    {(['de','en'] as const).map((l,i)=>{const [d,t]=progressOf(scans[l]);return <div className="ap-tcard" key={l}><div className="ap-tcardHead">{l==='de'?'Deutsch':'Englisch'}<span className="ap-tcardNo">#0{i+3}</span></div><div className="ap-tcardValue">{percent(d,t).toLocaleString('de-DE')}<small>%</small></div><div style={{display:'grid',gap:5}}><div className="ap-meter"><i style={{width:`${percent(d,t)}%`}}/></div><div className="ap-tcardFoot">{fmt(d)} / {fmt(t)} im Lauf</div></div></div>})}
    <div className="ap-tcard"><div className="ap-tcardHead">Offene Fälle<span className="ap-tcardNo">#05</span></div><div className="ap-tcardValue">{fmt(openCases)}</div><div className="ap-tcardFoot">{fmt(reviews.total)} Zuordnungen mit Beleg{ebayOpen?` · ${fmt(ebayOpen)} eBay`:''}</div></div>
    <div className="ap-tcard"><div className="ap-tcardHead">Preis-Trend<span className="ap-tcardNo">#06</span></div><div className="ap-tcardValue">{index?.guidePrices?((index.guidePrices.de?.publish||0)+(index.guidePrices.en?.publish||0)).toLocaleString('de-DE'):'–'}</div><div className="ap-tcardFoot">Varianten mit offiziellem Cardmarket-Preis</div></div>
   </div>
  </header>
  {statusError&&<p role="alert" className="ap-callout" style={{'--c':'var(--ap-warn)'} as React.CSSProperties}>{statusError}</p>}

  <nav className="ap-tabs" id="ap-tabs" role="tablist" aria-label="Bereiche">
   {([['scanner','Scanner',0],['sets','Set-Listen & Tempo',index?.reviewGroups.total||0],['pruefungen','Prüfungen',openCases],['ebay','eBay',ebayOpen]] as [Tab,string,number][]).map(([id,label,count])=><button key={id} type="button" role="tab" aria-selected={tab===id} className="ap-tab" onClick={()=>setTab(id)}>{label}{count>0&&<span className="ap-count">{fmt(count)}</span>}</button>)}
  </nav>

  {tab==='scanner'&&<section aria-label="Cardmarket-Scanner" style={{display:'grid',gap:14}}>
   <div className="ap-panel">
    <div className="ap-panelHead"><div><h2>Browser-Sitzung</h2><p className="ap-hint">Edge-Profil {session?.profileExists?'gespeichert':'nicht gefunden'} · geprüft {session?.checkedAt?new Date(session.checkedAt).toLocaleString('de-DE'):'–'}{(de?.sessionCheckAgeSeconds??0)>180?' (älter als 3 Minuten)':''}</p></div>
     <div className="ap-row"><span className={'ap-energy '+(session?.status==='AVAILABLE'?'ap-ok':session?.status==='BLOCKED'?'ap-bad':'ap-idle')}>{session?.status==='AVAILABLE'?'Cardmarket erreichbar':session?.status==='BLOCKED'?'Schutzseite':'unklar'}</span><span className={'ap-energy '+(session?.login==='AUTHENTICATED'?'ap-ok':'ap-warn')}>{session?.login==='AUTHENTICATED'?'Eingeloggt':session?.login==='LOGIN_REQUIRED'?'Gastmodus':'Login ungeklärt'}</span></div></div>
    {de&&de.status==='BLOCKED'&&de.lastIncident&&<div className="ap-callout" style={{'--c':'var(--ap-bad)'} as React.CSSProperties}><strong>Letzter Abbruch durch Cardmarket</strong><span>{de.lastIncident.cardId?de.lastIncident.cardId+' · ':''}{de.lastIncident.at?new Date(de.lastIncident.at).toLocaleString('de-DE')+' · ':''}{providerStageLabel[de.lastIncident.stage||de.lastIncident.kind||'']||'Anbieteranfrage'}{de.lastIncident.httpStatus?' · HTTP '+de.lastIncident.httpStatus:''}</span></div>}
    {de&&<div className="ap-row">
     <button className="ap-btn ap-btnGold" disabled={cardmarketResuming||cardmarketResetting||de.status==='RUNNING'||de.cooldownActive||session?.status==='BLOCKED'} title={session?.status==='BLOCKED'?'Cloudflare-Prüfung in Edge bestätigen':de.cooldownActive?'Schutzpause bis '+(de.nextAllowedAt?new Date(de.nextAllowedAt).toLocaleString('de-DE'):'Freigabe'):'Scan fortsetzen'} onClick={()=>void resumeCardmarket()}>{cardmarketResuming?'Start wird angefordert …':'▶ Scan fortsetzen'}</button>
     {(session?.status==='BLOCKED'||de.cooldownBlockingStatus==='BLOCKED')&&<button className="ap-btn" disabled={cardmarketResuming||cardmarketResetting} onClick={()=>void resumeCardmarket()}>Freigabe prüfen</button>}
     <button className="ap-btn" disabled={cardmarketResuming||cardmarketResetting} onClick={()=>void resetCardmarketScan()}>{cardmarketResetting?'Wird neu eingeplant …':'↻ Komplett neu scannen (DE + EN)'}</button>
    </div>}
    {cardmarketResumeMessage&&<small role="status">{cardmarketResumeMessage}</small>}
    <p className="ap-hint">Eine Anmeldung ist nicht nötig, solange die gefilterten Angebote öffentlich vollständig sind. Bei einer Cloudflare-Box prüft der Wächter alle zwei Minuten und meldet sich nach 5 Minuten per Telegram.</p>
   </div>
   <div className="ap-grid2">
   {(['de','en'] as const).map(lang=>{const s=scans[lang];const [cls,label]=scanState(s,lang);const [checkpoint,checkpointTotal]=progressOf(s);
    return <article className="ap-panel" key={lang}>
     <div className="ap-panelHead"><h3>Cardmarket · {lang==='de'?'Deutsch':'Englisch'}</h3><span className={'ap-energy '+cls}>{label}</span></div>
     {!s?<p className="ap-hint">Keine Scandaten verfügbar.</p>:<>
     {s.cooldownActive&&s.status!=='RUNNING'&&<div className="ap-callout" style={{'--c':s.cooldownBlockingStatus==='BLOCKED'?'var(--ap-bad)':'var(--ap-warn)'} as React.CSSProperties}><strong>{s.localCooldownActive?'Schutzpause dieser Sprache':'Wartet auf '+s.cooldownBlockingLanguage?.toUpperCase()}</strong><span>{s.cooldownBlockingStatus==='BLOCKED'?'Geht von selbst weiter, sobald die Cloudflare-Box in Edge bestätigt ist.':s.cooldownBlockingStatus==='PROVIDER_TIMEOUT'?'Anbieter antwortet nicht – 90 Minuten Pause.':s.cooldownBlockingStatus==='CONNECTION_LOST'?'Verbindung verloren – 60 Minuten Pause.':s.cooldownBlockingStatus==='BATCH_COMPLETE_MORE_PENDING'?'Normale Pause zwischen zwei Paketen.':readable(s.cooldownBlockingStatus||'Wartend')} Nächster Versuch {s.nextAllowedAt?new Date(s.nextAllowedAt).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'}):'offen'}.</span></div>}
     <div><div className="ap-big">{fmt(checkpoint)} <small>/ {fmt(checkpointTotal)} · {percent(checkpoint,checkpointTotal).toLocaleString('de-DE')} %</small></div><p className="ap-hint" style={{margin:'6px 0 8px'}}>Fortschritt des aktuellen Laufs · zuletzt {s.collectorUpdatedAt?new Date(s.collectorUpdatedAt).toLocaleString('de-DE'):'unbekannt'}</p><Progress done={checkpoint} total={checkpointTotal}/></div>
     <div className="ap-stats"><div className="ap-stat"><b>{fmt(s.pricedVariants)}</b><span>mit Preis</span></div><div className="ap-stat"><b>{fmt(s.missingVariants)}</b><span>ohne Preis</span></div><div className="ap-stat"><b>{fmt(s.problemCountCurrentCycle??s.problemCountInObserved)}</b><span>Prüffälle</span></div></div>
     <div className="ap-row">{s.problemCountInObserved>0&&<button className="ap-btn" onClick={()=>goToCases(lang)}>{fmt(s.problemCountCurrentCycle??s.problemCountInObserved)} Prüffälle ansehen →</button>}<button className="ap-btn" onClick={()=>setShowHistory(v=>v===lang?null:lang)}>{showHistory===lang?'Verlauf schließen':'Letzte Schritte'}</button></div>
     {showHistory===lang&&<div className="ap-chips" style={{flexDirection:'column'}}>{s.recentEvents.map((x,i)=><span key={i} className="ap-chip" style={{fontWeight:600}}>{x.at?new Date(x.at).toLocaleTimeString('de-DE'):''} · {x.cardId} · {readable(x.status)}</span>)}</div>}
     <details className="ap-details"><summary>Technische Details</summary>
      <div>{fmt(s.uniqueCards)} Karten · {fmt(s.totalVariants)} Varianten · {fmt(s.productMapped)} mit bestätigter Produktseite · {fmt(s.noExactSearchMatch)} Suchen ohne eindeutigen Treffer · {fmt(s.feedOnly)} Bulk-Varianten aus dem Preis-Trend · {fmt(s.browserMissingPriority)} fehlende Preise mit Browser-Priorität</div>
      <div>Kartenvarianten mit Beobachtung: <b>{fmt(s.browserProcessed)}</b> insgesamt{s.rescanStartedAt?<> · <b>{fmt(s.rescanProcessed||0)}</b> seit Neuscan am {new Date(s.rescanStartedAt).toLocaleDateString('de-DE')} · {fmt(s.currentCycleIssues||0)} Fehlerfälle bei {fmt(s.currentCycleObserved||0)} Beobachtungen</>:null}</div>
      <div><b>Filter-Vorprüfung:</b> {fmt(s.missingFilterInputs||0)} Varianten mit ungewöhnlicher Filterangabe · {fmt(s.nonfilterableSpecialPrints||0)} mit Sondermerkmalen, die Cardmarket nicht filtern kann (nicht automatisch falsch).</div>
      <div>Zuletzt geprüft: <b>{s.lastCard||'—'}</b>{s.lastResultStatus?' · '+readable(s.lastResultStatus):''} · Monitoring berechnet {s.statusSnapshotAt?new Date(s.statusSnapshotAt).toLocaleString('de-DE'):'–'}</div>
     </details></>}
    </article>})}
   </div>
  </section>}

  {tab==='sets'&&<CardmarketIndexPanel s={index} error={indexError} onReload={()=>void loadIndex()}/>}

  {tab==='pruefungen'&&<section aria-label="Offene Prüfungen" style={{display:'grid',gap:14}}>
   <div className="ap-panelHead">
    <div className="ap-row" role="tablist" aria-label="Art der Prüfung">
     <button type="button" role="tab" aria-selected={reviewArea==='fehler'} className={'ap-btn'+(reviewArea==='fehler'?' ap-btnGold':'')} onClick={()=>setReviewArea('fehler')}>Scanfehler <span className="ap-count" style={{background:reviewArea==='fehler'?'#0003':undefined}}>{fmt(failures.total)}</span></button>
     <button type="button" role="tab" aria-selected={reviewArea==='zuordnung'} className={'ap-btn'+(reviewArea==='zuordnung'?' ap-btnGold':'')} onClick={()=>setReviewArea('zuordnung')}>Cardmarket-Zuordnung <span className="ap-count" style={{background:reviewArea==='zuordnung'?'#0003':undefined}}>{fmt(reviews.total)}</span></button>
    </div>
    {user&&<div className="ap-row" role="group" aria-label="CSV-Export">{(['de','en'] as const).map(language=><button key={language} type="button" className="ap-btn" disabled={exportingFailureLang!==null} onClick={()=>void exportFailures(language)}>{exportingFailureLang===language?'Export läuft …':'⬇ CSV '+(language==='de'?'Deutsch':'Englisch')}</button>)}</div>}
   </div>
   {failureExportError&&<p role="alert">{failureExportError}</p>}

   {reviewArea==='fehler'&&<div className="ap-panel">
    <div className="ap-filters"><select aria-label="Prüfbereich" value={failureKind} onChange={e=>{setFailureKind(e.target.value as typeof failureKind);setFailurePage(0);setSelectedIssue(null);setIssueReview(null)}}><option value="karten">Karten-Zuordnungen</option><option value="preise">Technische Preisprüfungen</option><option value="drucke">Offene Sonderdrucke</option><option value="verknuepft">ID verknüpft (Stempel ohne Filter)</option><option value="technik">Browser-/Anbieterfehler</option><option value="alle">Alle Prüfungen</option></select><select aria-label="Fehlersprache" value={failureLang} onChange={e=>{setFailureLang(e.target.value as 'de'|'en');setFailurePage(0)}}><option value="de">Deutsch</option><option value="en">Englisch</option></select><select aria-label="Scanfehler Zeitraum" value={failureScope} onChange={e=>{setFailureScope(e.target.value as 'current'|'all');setFailurePage(0)}}><option value="current">Aktueller Neuscan</option><option value="all">Gesamter Verlauf</option></select><input aria-label="Scanfehler suchen" placeholder="Karte, Set, Fehler oder Produkt-ID" value={failureSearch} onChange={e=>{setFailureSearch(e.target.value);setFailurePage(0)}}/><button className="ap-btn" onClick={()=>void loadFailures()}>Aktualisieren</button></div>
    <div className="ap-chips">{([['Zuordnungen',failures.assignment,'ZUORDNUNG'],['Preisabfragen',failures.priceChecks||0,'PREISPRUEFUNG'],['Sonderdrucke',failures.printChecks||0,'DRUCKPRUEFUNG'],['Stempel',failures.linkedStamps||0,'ID_VERKNUEPFT_STEMPEL'],['Technik',failures.technical,'TECHNISCH'],['Daten fehlen',failures.missingData||0,'DATEN_FEHLEN']] as [string,number,string][]).map(([l,n,t])=><span key={t} className="ap-energy" style={{'--c':typeColor[t]} as React.CSSProperties}>{fmt(n)} {l}</span>)}</div>
    {failureError&&<p role="alert">{failureError}</p>}{retryFeedback&&<p role="status" className="ap-hint">{retryFeedback}</p>}
    <div className="ap-cases">
    {failures.items.map(p=>{const key=p.language+'|'+p.cardId+'|'+p.variantId;const stamp=p.printStamp&&p.printStamp!=='[]'?p.printStamp.replace(/[\[\]"]/g,''):'';const g=p.officialProductGuide;
     return <div key={key} className="ap-case" style={{'--c':typeColor[p.type]} as React.CSSProperties}>
      <div className="ap-caseHead"><div><div className="ap-caseName">{p.name} <span style={{color:'var(--ap-muted)',fontWeight:700}}>· {p.cardId}</span></div><div className="ap-caseMeta">{p.language.toUpperCase()} · Set {p.setId}{p.productId?' · Produkt '+p.productId:''} · {p.seenAt?new Date(p.seenAt).toLocaleString('de-DE'):''}</div></div>
       <div className="ap-row"><span className="ap-energy" style={{'--c':typeColor[p.type]} as React.CSSProperties}>{typeLabel[p.type]||p.type}</span></div></div>
      <div className="ap-chips">{stamp&&<span className="ap-chip">Stempel {stamp}</span>}{p.printFoil&&<span className="ap-chip">Foil {p.printFoil}</span>}{g&&<><span className="ap-chip">Ø 30 T {eur(g.avg30)}</span><span className="ap-chip">Trend {eur(g.trend)}</span><span className="ap-chip">Trend Holo {eur(g.trend_holo)}</span></>}{p.filterMode&&<span className="ap-chip">Filter {p.filterMode==='CANONICAL_URL_DOM_VERIFIED'?'Adresse':p.filterMode==='FORM_SUBMISSION_DOM_VERIFIED'?'Formular':p.filterMode}</span>}</div>
      <div className="ap-caseBody">
       <span>{p.type==='ID_VERKNUEPFT_STEMPEL'?'Produkt-ID verknüpft. Preisfreigabe braucht eine Bestätigung des genauen Drucks.':p.type==='ZUORDNUNG'?'Produkt-/Set-Zuordnung prüfen.':p.type==='DRUCKPRUEFUNG'?'Karte gefunden – nur Sonderdruck/Stempel zu klären.':p.type==='PREISPRUEFUNG'?'Zuordnung passt. Die Angebote konnten nicht vollständig gelesen werden – nichts zu tun, wird erneut versucht.':p.type==='TECHNISCH'?'Browser-/Anbieterproblem, wird automatisch erneut versucht.':p.type==='DATEN_FEHLEN'?'Kartendaten fehlen: '+(p.missingFields?.join(', ')||''):''}</span>
       {p.scoreMatchState&&<span><b>Set-/Nummern-Abgleich:</b> {p.scoreMatchState==='MULTIPLE_SAME_SET_NUMBER_CANDIDATES'?'Mehrere passende Produktversionen – keine automatische Druckzuordnung':p.scoreMatchState==='SET_NOT_INDEPENDENTLY_VERIFIED'?'Nummer passt, Set noch nicht sicher bestätigt':p.scoreMatchState==='UNIQUE_SET_NUMBER_PAGE_CANDIDATE'?'Ein Kandidat im geprüften Set – Druck noch offen':p.scoreMatchState}</span>}
       {Boolean(p.scoreCandidateUrls?.length)&&<span className="ap-row">{p.scoreCandidateUrls?.map((u,i)=><a key={u} href={u} target="_blank" rel="noopener noreferrer">Kandidat {i+1} ↗</a>)}</span>}
       {p.specialPrintComments&&<span className="ap-hint">Verkäuferkommentare ({p.specialPrintComments.target}, nur Hinweise): {p.specialPrintComments.counts.positive} eindeutig · {p.specialPrintComments.counts.shorthand_hint||0} Kürzel · {p.specialPrintComments.counts.contradiction} widersprüchlich · {p.specialPrintComments.counts.ambiguous} unklar · {p.specialPrintComments.counts.missing} ohne Angabe.</span>}
      </div>
      <div className="ap-row"><button className="ap-btn" disabled={retryingFailure!==null} onClick={()=>void retryFailedCard(p)}>{retryingFailure===key?'Wird eingeplant …':'↻ Erneut testen'}</button>{p.type!=='PREISPRUEFUNG'&&<button className="ap-btn" onClick={()=>void openIssue(p.language,p.cardId,p.variantId)}>{selectedIssue===key?'Schließen':'Fall prüfen'}</button>}</div>
      {selectedIssue===key&&(issueReview?<CardReview entry={issueReview} scanIssue={{status:p.status,detail:p.detail}} onSaved={()=>{setSelectedIssue(null);setIssueReview(null);void loadReviews();void loadFailures()}}/>:<small>{issueInfo||'Wird geladen …'}</small>)}
     </div>})}
    </div>
    {!failures.items.length&&!failureError&&<p className="ap-hint">Für diesen Filter gibt es keine offenen Fälle. 🎉</p>}
    <div className="ap-pager"><button className="ap-btn" disabled={failurePage===0} onClick={()=>setFailurePage(p=>p-1)}>← Zurück</button><span className="ap-hint">Seite {failurePage+1} · {fmt(failures.total)} Fälle</span><button className="ap-btn" disabled={(failurePage+1)*50>=failures.total} onClick={()=>setFailurePage(p=>p+1)}>Weiter →</button></div>
   </div>}

   {reviewArea==='zuordnung'&&<div className="ap-panel">
    <div className="ap-filters"><select aria-label="Sprache" value={reviewLang} onChange={e=>{setReviewLang(e.target.value as 'de'|'en');setReviewPage(0)}}><option value="de">Deutsch</option><option value="en">Englisch</option></select><select aria-label="Prüfstatus" value={reviewStatus} onChange={e=>{setReviewStatus(e.target.value as typeof reviewStatus);setReviewPage(0)}}><option value="PENDING_REVIEW">Offene Zuordnungen</option><option value="CONFIRMED_PRINT">Bestätigte Zuordnungen rückgängig machen</option><option value="NO_MATCH">Als kein Treffer markiert</option><option value="DEFERRED">Zurückgestellte Karten</option></select><input aria-label="Prüffälle durchsuchen" placeholder="Karte, Set oder Nummer suchen" value={reviewSearch} onChange={e=>{setReviewSearch(e.target.value);setReviewPage(0)}}/><button className="ap-btn" onClick={()=>void loadReviews()}>Aktualisieren</button></div>
    {reviewError&&<p role="alert">{reviewError}</p>}
    <div className="ap-row"><span className="ap-hint">{fmt(reviews.total)} {reviewStatus!=='PENDING_REVIEW'?'bereits bearbeitete Fälle':showAllCandidateCases||reviewSearch.trim()?'gespeicherte offene Zuordnungen':'Fälle mit konkretem Versionsbeleg'} · Seite {reviewPage+1}{reviewLoading?' · lädt …':''}</span><button className="ap-btn" onClick={()=>{setShowAllCandidateCases(v=>!v);setReviewPage(0)}}>{showAllCandidateCases?'Nur prüfbare Fälle':'Alle automatischen Nachprüfungen'}</button></div>
    {reviewStatus==='PENDING_REVIEW'&&!showAllCandidateCases&&!reviewSearch.trim()&&<p className="ap-hint">{fmt(Math.max(0,(reviews.allPending||0)-reviews.total))} weitere Fälle recherchiert der Scanner zuerst selbst. Keine Produkt-IDs raten.{reviews.recheck?.lastAuditedAt?' Letzter Katalogabgleich: '+new Date(reviews.recheck.lastAuditedAt).toLocaleString('de-DE'):''}</p>}
    <div style={{display:'grid',gap:12}}>{reviews.items.map(entry=><CardReview key={entry.card_id+entry.variant_id} entry={entry} onSaved={()=>void loadReviews()} onViewRelated={id=>{setReviewSearch('card:'+id);setReviewPage(0);setShowAllCandidateCases(true)}}/>)}</div>
    {!reviews.items.length&&!reviewLoading&&<p className="ap-hint">Keine offenen Fälle für diesen Filter.</p>}
    <div className="ap-pager"><button className="ap-btn" disabled={reviewPage===0} onClick={()=>setReviewPage(p=>p-1)}>← Zurück</button><button className="ap-btn" disabled={(reviewPage+1)*50>=reviews.total} onClick={()=>setReviewPage(p=>p+1)}>Nächste 50 →</button></div>
   </div>}
  </section>}

  {tab==='ebay'&&<section aria-label="eBay" style={{display:'grid',gap:14}}>
   <EbaySoldPanel s={ebaySold} error={ebaySoldError} onReload={()=>void loadEbaySold()}/>
   <div className="ap-panel">
    <div className="ap-panelHead"><div><h3>Alte eBay-Preisabfrage je Set</h3><p className="ap-hint">Früherer Sammler über die API, seit 12.11. von eBay blockiert. Verkaufswerte kommen jetzt vom Verkaufsscanner oben.</p></div><span className="ap-energy ap-idle">Pausiert</span></div>
    <div className="ap-sets">{sets.map(set=>{const job=jobs?.jobs.find(x=>x.id===set.id);const n=ebay.filter(x=>x.setId===set.id);const priced=n.filter(x=>x.price!=null).length;const target=ebayCount[set.id]||0;
     return <div className="ap-set" key={set.id}><b>{set.name}</b><div className="ap-bar" style={{height:6}}><i style={{width:`${percent(priced,target)}%`}}/></div><span className="ap-hint">{fmt(priced)} / {fmt(target)} mit Preis · {job?readable(job.status):'kein aktiver Scan'}</span>{job&&job.total>0&&<span className="ap-hint">{fmt(job.done)} / {fmt(job.total)} geprüft</span>}<button className="ap-btn" disabled={starting!==null||job?.running===true||jobs?.collectorActive===true} onClick={()=>void startSet(set.id)}>{starting===set.id?'Startet …':job?.running?'Läuft …':'Set-Scan starten'}</button></div>})}</div>
   </div>
   <div className="ap-panel">
    <div className="ap-panelHead"><h3>Offene eBay-Prüfungen <span className="ap-count">{fmt(openEbay.length)}</span></h3><div className="ap-filters"><input aria-label="eBay Fälle suchen" placeholder="Karte, Nummer oder Set suchen" value={ebaySearch} onChange={e=>setEbaySearch(e.target.value)}/><button className="ap-btn" onClick={()=>void loadEbay()}>Aktualisieren</button></div></div>
    {ebayError&&<p role="alert">{ebayError}</p>}
    <div className="ap-cases">{openEbay.map(e=><article key={e.cardId} className="ap-case" style={{'--c':'#3c7fb5'} as React.CSSProperties}><div className="ap-caseHead"><div><div className="ap-caseName">{e.name} · {e.number}</div><div className="ap-caseMeta">{e.setId} · {e.reviewReasons?.join(' · ')||readable(e.status)}</div></div><button className="ap-btn" onClick={()=>setExpanded(v=>v===e.cardId?null:e.cardId)}>{expanded===e.cardId?'Schließen':'Angebote prüfen'}</button></div>{expanded===e.cardId&&<div style={{borderTop:'1px solid var(--ap-line)',paddingTop:12}}><EbayAllSearchEvidence cardId={e.cardId}/><EbayCompactReview cardId={e.cardId} review={e.review} onSaved={()=>{setExpanded(null);void loadEbay()}}/></div>}</article>)}</div>
    {!openEbay.length&&<p className="ap-hint">Keine offenen eBay-Prüfungen.</p>}
   </div>
  </section>}
 </div>
 </AppShell>;
}
