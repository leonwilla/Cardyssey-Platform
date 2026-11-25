'use client';
import {useState} from 'react';
type Hour={hour:string;pages:number;prices:number;blocks:number;indexDirect:number};
type Group={group:string;set:string;kind:string;de:number;en:number;examples:string};
type Backlog=Record<string,number>;
export type IndexSnapshot={checkedAt:string;guidePrices?:{checkedAt?:string;guideDate?:string;changedRows?:number;de?:Record<string,number>;en?:Record<string,number>}|null;fullRescan?:{ready:boolean;setListsComplete:boolean;openRescans:number};baseline:{window:string;pagesPerHour:number;pricesPerHour:number};
 speed:{hours:Hour[];pagesPerHour:number;pricesPerHour:number;blocks:number};
 index:{plannedExpansions:number;completeExpansions:number;pagesDone:number;pagesPlanned:number;statuses:Record<string,number>;lastRun?:{status?:string;updated_at?:string;pages?:number}};
 backlog:Record<string,Backlog>;reviewGroups:{total:number;variants:number;top:Group[]};
 clearance:{session?:string;login?:string;waitingSince?:string|null;lastBlockAt?:string|null;note:string};
 imports:Record<string,{automatic_standard_candidates?:number}|null>};
export const num=(n:number|undefined)=>(n||0).toLocaleString('de-DE');
export const shortTime=(s?:string|null)=>s?new Date(s).toLocaleString('de-DE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'–';
const kind:Record<string,string>={plain:'normale Karte, mehrere Versionen','holo-vs-normal':'Holo und Normal gleiche Seite',masterball:'Meisterball',pokeball:'Pokéball',energy:'Energie','set-logo':'Set-Logo',staff:'Staff','1st-edition':'1. Auflage',shadowless:'Schattenlos'};

/** Prices per hour as gold bars; a red dot marks hours with a Cloudflare box. */
export function HourBars({hours}:{hours:Hour[]}){
 const max=Math.max(1,...hours.map(h=>h.prices));
 return <div>
  <div className="ap-hours" role="img" aria-label="Fertige Preise pro Stunde">
   {hours.map(h=>{const label=new Date(h.hour).toLocaleTimeString('de-DE',{hour:'2-digit'});return <div className="ap-hour" key={h.hour} title={`${label} Uhr: ${h.prices} Preise, ${h.pages} Seiten${h.blocks?`, ${h.blocks}× Cloudflare`:''}`}>
    {h.prices>0&&<span className="ap-hourVal">{h.prices}</span>}
    <div className={'ap-hourBar'+(h.prices?'':' zero')} style={{height:`${Math.max(3,h.prices/max*78)}%`}}/>
    {h.blocks>0?<span className="ap-hourBlock"/>:<span style={{height:6}}/>}
    <span className="ap-hourLbl">{label}</span>
   </div>})}
  </div>
  <div className="ap-legend"><span><i style={{background:'linear-gradient(180deg,#e4bd6a,#b98742)'}}/>fertige Preise</span><span><i style={{background:'#c4462f',borderRadius:'50%'}}/>Cloudflare-Box in dieser Stunde</span></div>
 </div>;
}

export function CardmarketIndexPanel({s,error,onReload}:{s:IndexSnapshot|null;error:string;onReload:()=>void}){
 const [open,setOpen]=useState(false);
 if(error)return <section className="ap-panel"><p role="alert">{error}</p></section>;
 if(!s)return <section className="ap-panel">Set-Listen-Scan lädt …</section>;
 const rescan=(l:string)=>(s.backlog[l]?.rescanCorrected||0)+(s.backlog[l]?.rescanFailed||0);
 const special=(s.backlog.de?.['status:SPECIAL_NOT_SEPARABLE']||0)+(s.backlog.en?.['status:SPECIAL_NOT_SEPARABLE']||0);
 return <section className="ap-panel" aria-label="Cardmarket Set-Listen-Scan">
  <div className="ap-panelHead"><div><h3>Tempo der letzten Stunden</h3><p className="ap-hint">Produktseiten direkt aus Cardmarkets Set-Listen · Stand {shortTime(s.checkedAt)} · vorher {num(s.baseline.pricesPerHour)} Preise/h ({s.baseline.window})</p></div><button type="button" className="ap-btn" onClick={onReload}>Aktualisieren</button></div>
  <HourBars hours={s.speed.hours}/>
  <div className="ap-facts">
   <div className="ap-fact"><span>Set-Listen gesammelt</span><b>{num(s.index.completeExpansions)} / {num(s.index.plannedExpansions)}</b><div className="ap-bar"><i style={{width:`${Math.min(100,s.index.pagesDone/(s.index.pagesPlanned||1)*100)}%`}}/></div><small className="ap-hint">{num(s.index.pagesDone)} / {num(s.index.pagesPlanned)} Listenseiten · letzter Lauf {s.index.lastRun?.status||'–'} {shortTime(s.index.lastRun?.updated_at)}</small></div>
   <div className="ap-fact"><span>Karten mit Cardmarket-Adresse</span>{(['de','en'] as const).map(l=><div key={l} style={{display:'grid',gap:3}}><b style={{fontSize:14}}>{l.toUpperCase()} {num(s.backlog[l]?.withUrl)} / {num(s.backlog[l]?.total)}</b><div className="ap-bar" style={{height:6}}><i style={{width:`${Math.min(100,(s.backlog[l]?.withUrl||0)/(s.backlog[l]?.total||1)*100)}%`}}/></div></div>)}</div>
   <div className="ap-fact"><span>Preis-Trend (offiziell, täglich)</span><b>{num(s.guidePrices?.de?.publish)} DE · {num(s.guidePrices?.en?.publish)} EN</b><small className="ap-hint">Preisliste vom {shortTime(s.guidePrices?.guideDate)} · übernommen {shortTime(s.guidePrices?.checkedAt)}</small><a className="ap-btn" style={{justifySelf:'start',padding:'5px 10px',fontSize:12}} href="/api/admin/cardmarket-index?download=guide-changes">Änderungsliste (CSV)</a></div>
   <div className="ap-fact"><span>Komplett-Neuscan</span><b>{s.fullRescan?.ready?<span className="ap-energy ap-ok">Jetzt sinnvoll</span>:<span className="ap-energy ap-idle">Noch nicht</span>}</b><small className="ap-hint">{s.fullRescan?.ready?'Alle Set-Listen gelesen, alte Fehlfälle neu gescannt. Oben „Komplett neu scannen“ drücken.':`${s.fullRescan?.setListsComplete?'Set-Listen fertig':'Set-Listen werden noch gesammelt'} · ${num(s.fullRescan?.openRescans)} alte Fehlfälle warten.`}</small></div>
  </div>
  <details className="ap-details"><summary>Warteschlange im Detail</summary>
   <div style={{display:'grid',gap:6}}>{(['de','en'] as const).map(l=><div key={l} className="ap-chips"><span className="ap-chip" style={{background:'var(--ap-accent)',color:'#fff'}}>{l.toUpperCase()}</span><span className="ap-chip">{num(s.backlog[l]?.neverScanned)} noch nie gescannt</span><span className="ap-chip">{num(rescan(l))} Neu-Scan alter Fehlfälle</span><span className="ap-chip">{num((s.backlog[l]?.doneViaIndex||0)+(s.backlog[l]?.alreadyComplete||0))} erledigt</span><span className="ap-chip">{num(s.backlog[l]?.['status:GUIDE_PRICE_BELOW_THRESHOLD'])} unter 20 € (Preis-Trend)</span><span className="ap-chip">{num(s.backlog[l]?.['status:SET_NOT_INDEXED'])} Set-Liste fehlt</span></div>)}
   <p className="ap-hint">Nicht in der Prüfliste: {num(special)} Sonderdrucke, die Cardmarket nicht als eigenes Produkt führt (z. B. Meisterball-Muster). Unter 20 € gilt der offizielle Preis-Trend, ab 20 € scannt der Browser den genauen Preis nach Sprache.</p></div>
  </details>
  <div style={{borderTop:'1px solid var(--ap-line)',paddingTop:14,display:'grid',gap:10}}>
   <div className="ap-panelHead"><div><h3>Varianten-Prüfgruppen <span className="ap-count">{num(s.reviewGroups.total)}</span></h3><p className="ap-hint">{num(s.reviewGroups.variants)} Varianten, die Cardmarket nicht per Filter trennt. Eine Regel pro Gruppe löst alle Karten darin.</p></div><div className="ap-row"><a className="ap-btn" href="/api/admin/cardmarket-index?download=review-groups">CSV herunterladen</a><button type="button" className="ap-btn" onClick={()=>setOpen(v=>!v)}>{open?'Ausblenden':'Größte Gruppen'}</button></div></div>
   {open&&<div className="ap-cases">{s.reviewGroups.top.map(g=><div key={g.group} className="ap-case" style={{'--c':'var(--ap-warn)'} as React.CSSProperties}><div className="ap-caseHead"><span className="ap-caseName">{g.set} · {kind[g.kind]||g.kind}</span><span className="ap-chips"><span className="ap-chip">{g.de} DE</span><span className="ap-chip">{g.en} EN</span></span></div><div className="ap-caseMeta">{g.examples}</div></div>)}</div>}
  </div>
 </section>;
}
