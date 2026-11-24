'use client';
import {useCallback,useEffect,useState} from 'react';
type Hour={hour:string;pages:number;prices:number;blocks:number;indexDirect:number};
type Group={group:string;set:string;kind:string;de:number;en:number;examples:string};
type Backlog=Record<string,number>;
type Snapshot={checkedAt:string;fullRescan?:{ready:boolean;setListsComplete:boolean;openRescans:number};baseline:{window:string;pagesPerHour:number;pricesPerHour:number};
 speed:{hours:Hour[];pagesPerHour:number;pricesPerHour:number;blocks:number};
 index:{plannedExpansions:number;completeExpansions:number;pagesDone:number;pagesPlanned:number;statuses:Record<string,number>;lastRun?:{status?:string;updated_at?:string;pages?:number}};
 backlog:Record<string,Backlog>;reviewGroups:{total:number;variants:number;top:Group[]};
 clearance:{session?:string;login?:string;waitingSince?:string|null;lastBlockAt?:string|null;note:string};
 imports:Record<string,{automatic_standard_candidates?:number}|null>};
const num=(n:number|undefined)=>(n||0).toLocaleString('de-DE');
const time=(s?:string|null)=>s?new Date(s).toLocaleString('de-DE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'–';
const kind:Record<string,string>={plain:'normale Karte, mehrere Versionen','holo-vs-normal':'Holo und Normal gleiche Seite',masterball:'Meisterball',pokeball:'Pokéball',energy:'Energie','set-logo':'Set-Logo',staff:'Staff','1st-edition':'1. Auflage',shadowless:'Schattenlos'};
function Bar({done,total}:{done:number;total:number}){return <div style={{height:10,borderRadius:8,background:'var(--border)',overflow:'hidden'}}><div style={{height:'100%',width:`${Math.min(100,done/(total||1)*100)}%`,background:'var(--accent,#b98742)'}}/></div>}
export function CardmarketIndexPanel(){
 const [s,setS]=useState<Snapshot|null>(null);const [error,setError]=useState('');const [open,setOpen]=useState(false);
 const load=useCallback(async()=>{try{const r=await fetch('/api/admin/cardmarket-index',{cache:'no-store'});if(!r.ok)throw Error();setS(await r.json());setError('')}catch{setError('Status des Set-Listen-Scans gerade nicht erreichbar')}},[]);
 useEffect(()=>{void load();const t=setInterval(()=>void load(),60000);return()=>clearInterval(t)},[load]);
 if(error)return <section className="statusPanel" style={{padding:18,marginBottom:20}}><p role="alert">{error}</p></section>;
 if(!s)return <section className="statusPanel" style={{padding:18,marginBottom:20}}>Set-Listen-Scan lädt …</section>;
 const factor=s.baseline.pricesPerHour?Math.round(s.speed.pricesPerHour/s.baseline.pricesPerHour):0;
 const rescan=(l:string)=>(s.backlog[l]?.rescanCorrected||0)+(s.backlog[l]?.rescanFailed||0);
 const waiting=s.clearance.waitingSince;
 return <section className="statusPanel" aria-label="Cardmarket Set-Listen-Scan" style={{padding:18,marginBottom:20,display:'grid',gap:14}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:10,flexWrap:'wrap',alignItems:'center'}}><div><strong>Cardmarket · Set-Listen-Scan (DE + EN)</strong><div style={{fontSize:12,opacity:.75}}>Produktseiten direkt aus Cardmarkets Erweiterungslisten statt Suche · Stand {time(s.checkedAt)}</div></div><button type="button" className="ghostButton" onClick={()=>void load()}>Aktualisieren</button></div>
  <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))',gap:10}}>
   <div><div style={{fontSize:12,opacity:.75}}>Fertige Preise pro Stunde</div><strong style={{fontSize:22}}>{num(s.speed.pricesPerHour)}</strong><div style={{fontSize:12}}>vorher {num(s.baseline.pricesPerHour)} ({s.baseline.window}){factor>1?` · etwa ${factor}× so viele`:''}</div></div>
   <div><div style={{fontSize:12,opacity:.75}}>Produktseiten pro Stunde</div><strong style={{fontSize:22}}>{num(s.speed.pagesPerHour)}</strong><div style={{fontSize:12}}>vorher {num(s.baseline.pagesPerHour)}</div></div>
   <div><div style={{fontSize:12,opacity:.75}}>Cloudflare</div><strong style={{fontSize:16}}>{waiting?'wartet auf Bestätigung':s.clearance.session==='AVAILABLE'?'frei':s.clearance.session||'–'}</strong><div style={{fontSize:12}}>{waiting?'seit '+time(waiting)+' · in Edge F5 + Kästchen':'letzte Schutzseite '+time(s.clearance.lastBlockAt)}{s.clearance.login==='AUTHENTICATED'?' · eingeloggt':s.clearance.login==='LOGIN_REQUIRED'?' · nicht eingeloggt':''}</div></div>
   <div><div style={{fontSize:12,opacity:.75}}>Automatisch übernehmbare Preise</div><strong style={{fontSize:22}}>{num(s.imports.de?.automatic_standard_candidates)} DE · {num(s.imports.en?.automatic_standard_candidates)} EN</strong></div>
  </div>
  <div style={{fontSize:12,display:'flex',gap:6,flexWrap:'wrap'}}>{s.speed.hours.map(h=><span key={h.hour} title={`${h.pages} Seiten, ${h.blocks} Schutzseiten`} style={{border:'1px solid var(--border)',borderRadius:6,padding:'2px 6px'}}>{new Date(h.hour).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'})}: <strong>{h.prices}</strong> Preise{h.blocks?` · ${h.blocks}× Schutz`:''}</span>)}</div>
  <div style={{display:'grid',gap:6}}><div style={{fontSize:13}}><strong>Set-Listen gesammelt:</strong> {num(s.index.completeExpansions)} / {num(s.index.plannedExpansions)} Erweiterungen · {num(s.index.pagesDone)} / {num(s.index.pagesPlanned)} Listenseiten · letzter Lauf {s.index.lastRun?.status||'–'} {time(s.index.lastRun?.updated_at)}</div><Bar done={s.index.pagesDone} total={s.index.pagesPlanned}/></div>
  <div style={{fontSize:13,display:'grid',gap:4}}><strong>Warteschlange mit direkter Adresse</strong>{['de','en'].map(l=><div key={l}>{l.toUpperCase()}: {num(s.backlog[l]?.neverScanned)} noch nie gescannt · {num(rescan(l))} alte Fehlfälle/Korrekturen werden neu gescannt (davon {num(s.backlog[l]?.rescanCorrected)} mit korrigierter ID zuerst) · {num((s.backlog[l]?.doneViaIndex||0)+(s.backlog[l]?.alreadyComplete||0))} erledigt · {num(s.backlog[l]?.['status:GUIDE_PRICE_BELOW_THRESHOLD'])} unter 2 € über Richtwert · {num(s.backlog[l]?.['status:SET_NOT_INDEXED'])} Set-Liste fehlt noch</div>)}</div>
  <div style={{fontSize:13,border:'1px solid var(--border)',borderRadius:8,padding:10}}><strong>Komplett-Neuscan:</strong> {s.fullRescan?.ready?'Jetzt sinnvoll. Alle Set-Listen gelesen und alte Fehlfälle neu gescannt. Oben bei Cardmarket „Komplett neu scannen (DE + EN)“ drücken, dann werden alle Preise einmal frisch geholt.':`Noch nicht. ${s.fullRescan?.setListsComplete?'Set-Listen fertig':'Set-Listen werden noch gesammelt'} · ${num(s.fullRescan?.openRescans)} alte Fehlfälle warten auf ihren Neu-Scan.`}</div>
  <div style={{fontSize:12,opacity:.8}}>Nicht in der Prüfliste: {num((s.backlog.de?.['status:SPECIAL_NOT_SEPARABLE']||0)+(s.backlog.en?.['status:SPECIAL_NOT_SEPARABLE']||0))} Sonderdrucke, die Cardmarket nicht als eigenes Produkt führt (z. B. Meisterball-Muster) · Karten unter 2 € laufen über den offiziellen Richtwert.</div>
  <div style={{borderTop:'1px solid var(--border)',paddingTop:12,display:'grid',gap:8}}>
   <div style={{display:'flex',justifyContent:'space-between',gap:10,flexWrap:'wrap',alignItems:'center'}}><div><strong>Varianten-Prüfgruppen: {num(s.reviewGroups.total)} Gruppen · {num(s.reviewGroups.variants)} Varianten</strong><div style={{fontSize:12,opacity:.75}}>Varianten, die Cardmarket nicht per Filter trennt. Eine Regel pro Gruppe löst alle Karten darin.</div></div><div style={{display:'flex',gap:8}}><a className="ghostButton" href="/api/admin/cardmarket-index?download=review-groups">CSV herunterladen</a><button className="ghostButton" onClick={()=>setOpen(v=>!v)}>{open?'Ausblenden':'Größte Gruppen'}</button></div></div>
   {open&&<div style={{display:'grid',gap:6}}>{s.reviewGroups.top.map(g=><div key={g.group} style={{fontSize:12,border:'1px solid var(--border)',borderRadius:8,padding:8}}><strong>{g.set} · {kind[g.kind]||g.kind}</strong> · {g.de} DE / {g.en} EN<div style={{opacity:.75}}>{g.examples}</div></div>)}</div>}
  </div>
 </section>;
}
