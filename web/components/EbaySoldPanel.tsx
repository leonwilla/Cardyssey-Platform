'use client';
import {num,shortTime} from '@/components/CardmarketIndexPanel';
type Hour={hour:string;pages:number;items:number;sales:number};
type Run={start:string;end:string|null;status:string;pages:number|null};
type Sale={title:string;eur:number;soldOn:string;lang:string;url:string};
export type EbaySoldSnapshot={checkedAt:string;health:'LÄUFT'|'WARTET'|'STEHT'|'PROBLEM';collectorStatus?:string;collectorStatusAt?:string|null;
 current?:{query:string;at:string;hits:number}|null;today:{pages:number;cap:number;perRun:number};queue:{size:number;done:number;due?:number|null};
 runs:Run[];hours:Hour[];recent:Sale[];
 totals:{sales?:number;cards?:number;sales24h?:number;newestSale?:string|null;variantsValued?:number;valuesUpdatedAt?:string|null;cardsChecked24h?:number;itemsSeen24h?:number;salesMatched24h?:number};
 import:{due?:number;importAt?:string;lastImport?:{pages:number;items:number;sales:number;variants_valued:number}}};
const HEALTH:Record<string,[string,string,string]>={
 'LÄUFT':['ap-ok','Läuft gerade','Liest gerade eBay-Seiten.'],
 'WARTET':['ap-idle','Wartet auf nächsten Lauf','Startet jede Stunde um :05 (Windows-Aufgabe „Cardyssey eBay Verkaufsscanner“).'],
 'STEHT':['ap-warn','Steht','Seit über 2 Stunden kein Lauf. Ist der Tiny an und die Windows-Aufgabe aktiv?'],
 'PROBLEM':['ap-warn','Braucht dich','Robot-Prüfung oder abgemeldet: Desktop-Verknüpfung „eBay Test-Browser (Cardyssey)“ öffnen, nur mit dem Käuferkonto anmelden.'],
};
const RUN:Record<string,string>={OK:'fertig',DAILY_CAP:'Tageslimit erreicht',BLOCKED_ROBOT_CHECK:'Robot-Prüfung',LOGIN_REQUIRED:'abgemeldet',NO_QUEUE:'keine Warteschlange','LÄUFT':'läuft',OHNE_ENDE:'ohne Ende-Meldung'};
const eur=(n:number)=>n.toLocaleString('de-DE',{style:'currency',currency:'EUR'});

export function EbaySoldPanel({s,error,onReload}:{s:EbaySoldSnapshot|null;error:string;onReload:()=>void}){
 if(error)return <section className="ap-panel"><p role="alert">{error}</p></section>;
 if(!s)return <section className="ap-panel">eBay-Verkaufsscanner lädt …</section>;
 const [cls,label,hint]=HEALTH[s.health]||HEALTH.WARTET;
 const max=Math.max(1,...s.hours.map(h=>h.pages));
 const t=s.totals;
 return <section className="ap-panel" aria-label="eBay-Verkaufsscanner">
  <div className="ap-panelHead"><div><h2>eBay · Verkaufsscanner</h2><p className="ap-hint">Liest eBay.de „verkaufte Artikel“ für seltene Karten im eigenen Edge-Profil · Stand {shortTime(s.checkedAt)}</p></div><div className="ap-row"><span className={'ap-energy '+cls}>{label}</span><button type="button" className="ap-btn" onClick={onReload}>Aktualisieren</button></div></div>
  <p className="ap-hint">{hint}{s.collectorStatus&&s.collectorStatus!=='OK'?` Letzte Meldung: ${RUN[s.collectorStatus]||s.collectorStatus} (${shortTime(s.collectorStatusAt)}).`:''}</p>
  <div>
   <div className="ap-hours" role="img" aria-label="Gelesene eBay-Seiten pro Stunde">
    {s.hours.map(h=>{const l=new Date(h.hour).toLocaleTimeString('de-DE',{hour:'2-digit'});return <div className="ap-hour" key={h.hour} title={`${l} Uhr: ${h.pages} Seiten, ${h.items} Treffer, ${h.sales} neue Verkäufe gespeichert`}>
     {h.pages>0&&<span className="ap-hourVal">{h.pages}</span>}
     <div className={'ap-hourBar'+(h.pages?'':' zero')} style={{height:`${Math.max(3,h.pages/max*78)}%`}}/>
     {h.sales>0?<span className="ap-hourBlock" style={{background:'#3c8f5a'}}/>:<span style={{height:6}}/>}
     <span className="ap-hourLbl">{l}</span>
    </div>})}
   </div>
   <div className="ap-legend"><span><i style={{background:'linear-gradient(180deg,#e4bd6a,#b98742)'}}/>gelesene Seiten</span><span><i style={{background:'#3c8f5a',borderRadius:'50%'}}/>neue Verkäufe gespeichert</span></div>
  </div>
  <div className="ap-facts">
   <div className="ap-fact"><span>Gerade bei</span><b style={{fontSize:15}}>{s.current?.query||'–'}</b><small className="ap-hint">{s.current?`${shortTime(s.current.at)} · ${num(s.current.hits)} Treffer auf der Seite`:''}</small></div>
   <div className="ap-fact"><span>Seiten heute</span><b>{num(s.today.pages)} / {num(s.today.cap)}</b><div className="ap-bar"><i style={{width:`${Math.min(100,s.today.pages/(s.today.cap||1)*100)}%`}}/></div><small className="ap-hint">bis zu {s.today.perRun} pro Stunde, 20–30 s Abstand</small></div>
   <div className="ap-fact"><span>Aktuelle Runde</span><b>{num(s.queue.done)} / {num(s.queue.size)} Karten</b><div className="ap-bar"><i style={{width:`${Math.min(100,s.queue.done/(s.queue.size||1)*100)}%`}}/></div><small className="ap-hint">{num(s.queue.due??undefined)} Karten warten insgesamt auf eine Prüfung</small></div>
   <div className="ap-fact"><span>Ergebnis</span><b>{num(t.variantsValued)} Varianten mit eBay-Wert</b><small className="ap-hint">{num(t.sales)} Verkäufe zu {num(t.cards)} Karten gespeichert · letzter Verkauf {t.newestSale||'–'}</small></div>
  </div>
  <div className="ap-chips">
   <span className="ap-chip">24 h: {num(t.cardsChecked24h)} Karten geprüft</span>
   <span className="ap-chip">{num(t.itemsSeen24h)} Verkäufe gelesen</span>
   <span className="ap-chip">{num(t.salesMatched24h)} passten genau zur Karte</span>
   <span className="ap-chip">Auswertung {shortTime(s.import.importAt)}{s.import.lastImport?`: ${s.import.lastImport.sales} neue Verkäufe, ${s.import.lastImport.variants_valued} Werte`:''}</span>
  </div>
  <p className="ap-hint">Nur Verkäufe, die eindeutig zu Name, Nummer, Sprache und Druckart passen, zählen. Sammelangebote („Auswahl“), gegradete Karten und Preisspannen fallen raus, deshalb ist die Trefferquote absichtlich niedrig.</p>
  <details className="ap-details"><summary>Letzte Läufe</summary>
   <div className="ap-chips">{[...s.runs].reverse().map(r=><span key={r.start} className="ap-chip">{shortTime(r.start)} · {RUN[r.status]||r.status}{r.pages!=null?` · ${r.pages} Seiten`:''}</span>)}</div>
  </details>
  <details className="ap-details"><summary>Neueste erkannte Verkäufe</summary>
   <div className="ap-cases">{s.recent.map(v=><div key={v.url||v.title} className="ap-case" style={{'--c':'#3c7fb5'} as React.CSSProperties}><div className="ap-caseHead"><span className="ap-caseName">{v.url?<a href={v.url} target="_blank" rel="noreferrer">{v.title}</a>:v.title}</span><span className="ap-chips"><span className="ap-chip">{eur(Number(v.eur))}</span><span className="ap-chip">{v.lang.toUpperCase()}</span><span className="ap-chip">verkauft {v.soldOn}</span></span></div></div>)}</div>
  </details>
 </section>;
}
