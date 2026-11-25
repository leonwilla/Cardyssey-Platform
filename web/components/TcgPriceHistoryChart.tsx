"use client";
import {useEffect,useMemo,useState} from 'react';

type Point={date:string;eur:number};
type HistoryResponse={points:Point[];recordedSince?:string|null};
const RANGES=[{days:7,label:'7 T'},{days:30,label:'30 T'},{days:90,label:'3 M'},{days:365,label:'1 J'},{days:0,label:'Alles'}] as const;
const DAY=86_400_000;
const format=(v:number)=>new Intl.NumberFormat('de-DE',{style:'currency',currency:'EUR'}).format(v);
const shortDate=(t:number)=>new Date(t).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit',year:'2-digit',timeZone:'UTC'});
const today=()=>{const d=new Date();return Date.UTC(d.getFullYear(),d.getMonth(),d.getDate())};

/** Cardmarket price (Near Mint) over time. The price holds until the next
 *  change, so the line is drawn as steps up to today. */
export function TcgPriceHistoryChart({cardId,language,variantId}:{cardId:string;language:string;variantId:string}){
 const [days,setDays]=useState<number>(30);
 const [data,setData]=useState<HistoryResponse>({points:[]});
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 const [hover,setHover]=useState<number|null>(null);
 useEffect(()=>{
  const controller=new AbortController();
  setLoading(true);setError('');setHover(null);
  const params=new URLSearchParams({language,variantId,days:String(days)});
  fetch(`/api/pricing/tcg-history/${encodeURIComponent(cardId)}?${params}`,{signal:controller.signal,cache:'no-store'})
   .then(async r=>{if(!r.ok)throw new Error('Preisverlauf derzeit nicht verfügbar');return await r.json() as HistoryResponse})
   .then(d=>{if(!controller.signal.aborted)setData({points:Array.isArray(d.points)?d.points:[],recordedSince:d.recordedSince})})
   .catch(err=>{if(!controller.signal.aborted)setError(err instanceof Error?err.message:'Fehler beim Preisverlauf')})
   .finally(()=>{if(!controller.signal.aborted)setLoading(false)});
  return ()=>controller.abort();
 },[cardId,language,variantId,days]);

 const chart=useMemo(()=>{
  const raw=data.points.map(p=>({t:Date.parse(p.date+'T00:00:00Z'),eur:p.eur})).filter(p=>Number.isFinite(p.t)&&p.eur>0).sort((a,b)=>a.t-b.t);
  if(!raw.length)return null;
  const end=today();
  const start=days>0?end-days*DAY:raw[0].t;
  // The value before the range start carries into the range.
  const before=raw.filter(p=>p.t<=start).at(-1);
  const steps=[...(before?[{t:start,eur:before.eur}]:[]),...raw.filter(p=>p.t>start)];
  const last=steps.at(-1)!;
  if(last.t<end)steps.push({t:end,eur:last.eur});
  const x0=steps[0].t,x1=Math.max(end,x0+DAY);
  let lo=Math.min(...steps.map(p=>p.eur)),hi=Math.max(...steps.map(p=>p.eur));
  const pad=Math.max((hi-lo)*.12,hi*.02,.05);lo=Math.max(0,lo-pad);hi+=pad;
  const W=620,H=190,L=58,R=12,T=14,B=26;
  const x=(t:number)=>L+(t-x0)/(x1-x0)*(W-L-R);
  const y=(v:number)=>T+(hi-v)/(hi-lo)*(H-T-B);
  let path='';
  steps.forEach((p,i)=>{path+=i?` H${x(p.t).toFixed(1)} V${y(p.eur).toFixed(1)}`:`M${x(p.t).toFixed(1)} ${y(p.eur).toFixed(1)}`});
  const area=`${path} V${H-B} H${x(steps[0].t).toFixed(1)} Z`;
  const first=steps[0].eur,change=first>0?(last.eur-first)/first*100:0;
  return {steps,path,area,x,y,W,H,L,R,T,B,lo,hi,x0,x1,first,last:last.eur,change,partial:days>0&&raw[0].t>start};
 },[data,days]);

 const hovered=chart&&hover!=null?chart.steps.filter(p=>p.t<=hover).at(-1)??chart.steps[0]:null;
 const onMove=(e:React.PointerEvent<SVGSVGElement>)=>{
  if(!chart)return;
  const box=e.currentTarget.getBoundingClientRect();
  const px=(e.clientX-box.left)/box.width*chart.W;
  const t=chart.x0+(px-chart.L)/(chart.W-chart.L-chart.R)*(chart.x1-chart.x0);
  setHover(Math.min(chart.x1,Math.max(chart.x0,t)));
 };
 const up=chart&&chart.change>=0;
 return <section className="ebayHistoryPanel tcgHistoryPanel" aria-label="Cardmarket-Preisverlauf">
  <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline',gap:12,flexWrap:'wrap'}}>
   <strong>Preisverlauf · Cardmarket</strong>
   {chart&&!loading?<span style={{fontWeight:800,fontSize:13,color:Math.abs(chart.change)<.05?'var(--secondary)':up?'#1d7a4f':'#b3402a'}}>
    {chart.change>0?'+':''}{chart.change.toFixed(1).replace('.',',')} % · {format(chart.first)} → {format(chart.last)}
   </span>:null}
  </div>
  <div className="editorMarketSwitch" role="tablist" aria-label="Zeitraum" style={{gridTemplateColumns:`repeat(${RANGES.length},1fr)`,margin:'12px 0'}}>
   {RANGES.map(r=><button key={r.days} type="button" role="tab" aria-selected={days===r.days} className={days===r.days?'selected':''} style={{minHeight:34,fontSize:13}} onClick={()=>setDays(r.days)}>{r.label}</button>)}
  </div>
  {loading&&!chart?<p>Preisverlauf wird geladen …</p>:error?<p>{error}</p>:!chart?<p style={{color:'var(--secondary)',fontSize:13}}>Für diese Karte wurde noch kein Cardmarket-Preis aufgezeichnet.</p>:<>
   <svg role="img" aria-label={`Cardmarket-Preis von ${format(chart.first)} auf ${format(chart.last)}`} viewBox={`0 0 ${chart.W} ${chart.H}`}
        style={{display:'block',width:'100%',maxHeight:260,touchAction:'pan-y',opacity:loading?.5:1}}
        onPointerMove={onMove} onPointerDown={onMove} onPointerLeave={()=>setHover(null)}>
    {[chart.hi,(chart.hi+chart.lo)/2,chart.lo].map((v,i)=><g key={i}>
     <line x1={chart.L} x2={chart.W-chart.R} y1={chart.y(v)} y2={chart.y(v)} stroke="currentColor" opacity=".12"/>
     <text x={chart.L-6} y={chart.y(v)+4} fontSize={11} fill="currentColor" opacity=".7" textAnchor="end">{format(v)}</text>
    </g>)}
    <path d={chart.area} fill="var(--light-accent, #158267)" opacity=".1"/>
    <path d={chart.path} stroke="var(--light-accent, #158267)" strokeWidth="2.5" fill="none" strokeLinejoin="round"/>
    <text x={chart.L} y={chart.H-6} fontSize={11} fill="currentColor" opacity=".7">{shortDate(chart.x0)}</text>
    <text x={chart.W-chart.R} y={chart.H-6} fontSize={11} fill="currentColor" opacity=".7" textAnchor="end">heute</text>
    {hovered&&hover!=null?<g>
     <line x1={chart.x(hover)} x2={chart.x(hover)} y1={chart.T} y2={chart.H-chart.B} stroke="currentColor" opacity=".35" strokeDasharray="3 3"/>
     <circle cx={chart.x(hover)} cy={chart.y(hovered.eur)} r={4.5} fill="var(--light-accent, #158267)"/>
     <text x={Math.min(chart.W-chart.R-4,Math.max(chart.L+4,chart.x(hover)))} y={chart.T+10} fontSize={12} fontWeight={800} fill="currentColor"
           textAnchor={chart.x(hover)>chart.W*.7?'end':chart.x(hover)<chart.W*.3?'start':'middle'}>{shortDate(hover)}: {format(hovered.eur)}</text>
    </g>:null}
   </svg>
   <small style={{color:'var(--secondary)'}}>
    Cardmarket-Preis dieser Sprache und Variante (ohne Zustandsabschlag).
    {chart.partial&&data.recordedSince?` Aufgezeichnet seit ${shortDate(Date.parse(data.recordedSince+'T00:00:00Z'))}, der Verlauf füllt sich täglich.`:''}
   </small>
  </>}
 </section>;
}
