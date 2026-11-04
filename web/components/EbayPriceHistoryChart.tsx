"use client";
import {useEffect,useMemo,useState} from 'react';

type HistoryPoint={soldOn:string;eur:number;condition:string;conditionAssumed:boolean;variantAssumed:boolean};
type HistoryResponse={points:HistoryPoint[]};

export function EbayPriceHistoryChart({cardId,language,variantId}:{cardId:string;language:string;variantId:string}){
 const [points,setPoints]=useState<HistoryPoint[]>([]);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 useEffect(()=>{
  const controller=new AbortController();
  setLoading(true);setPoints([]);setError('');
  const params=new URLSearchParams({language,variantId});
  fetch(`/api/pricing/history/${encodeURIComponent(cardId)}?${params}`,{signal:controller.signal,cache:'no-store'})
   .then(async r=>{if(!r.ok)throw new Error('Preisverlauf derzeit nicht verfügbar');return await r.json() as HistoryResponse})
   .then(data=>{if(!controller.signal.aborted)setPoints(Array.isArray(data.points)?data.points:[])})
   .catch(err=>{if(!controller.signal.aborted)setError(err instanceof Error?err.message:'Fehler beim Preisverlauf')})
   .finally(()=>{if(!controller.signal.aborted)setLoading(false)});
  return ()=>controller.abort();
 },[cardId,language,variantId]);
 const chart=useMemo(()=>{
  const sorted=points.filter(p=>p.eur>0&&Number.isFinite(p.eur)&&Number.isFinite(Date.parse(p.soldOn))).sort((a,b)=>a.soldOn.localeCompare(b.soldOn));
  const byDate=new Map<string,number[]>();
  sorted.forEach(p=>byDate.set(p.soldOn,[...(byDate.get(p.soldOn)||[]),p.eur]));
  const data=[...byDate.entries()].map(([date,values])=>{const s=[...values].sort((a,b)=>a-b);return {date,eur:s.length%2?s[(s.length-1)/2]:(s[s.length/2-1]+s[s.length/2])/2}});
  const minX=Date.parse(data[0]?.date??'')||0,maxX=Date.parse(data.at(-1)?.date??'')||minX+1;
  const minY=Math.min(...data.map(d=>d.eur)),maxY=Math.max(...data.map(d=>d.eur));
  const width=620,height=166,left=44,top=15,right=14,bottom=24;
  const x=(date:string)=>left+(Date.parse(date)-minX)/Math.max(1,maxX-minX)*(width-left-right);
  const y=(eur:number)=>top+(maxY-eur)/Math.max(.01,maxY-minY)*(height-top-bottom);
  return {data,poly:data.map(d=>`${x(d.date)},${y(d.eur)}`).join(' '),minY,maxY,width,height,left,top,bottom};
 },[points]);
 const format=(v:number)=>new Intl.NumberFormat('de-DE',{style:'currency',currency:'EUR'}).format(v);
 return <section className="ebayHistoryPanel" aria-label="eBay-Preisverlauf">
  <strong>eBay-Verlauf · verkaufte Karten</strong>
  <p style={{fontSize:12,margin:'5px 0 12px',color:'var(--secondary)'}}>Alle bisher erfassten Einzelverkäufe dieser Karte und Druckvariante, unabhängig vom Alter. Der heutige Marktwert verwendet ein eigenes rollierendes Median-Zeitfenster.</p>
  {loading?<p>Preisverlauf wird geladen …</p>:error?<p>{error}</p>:chart.data.length===0?<p style={{color:'var(--secondary)',fontSize:13}}>Noch keine historischen eBay-Verkäufe erfasst.</p>:<>
   <svg role="img" aria-label={`Preisverlauf aus ${points.length} Verkäufen zwischen ${chart.data[0].date} und ${chart.data.at(-1)?.date}`} viewBox={`0 0 ${chart.width} ${chart.height}`} style={{display:'block',width:'100%',maxHeight:260}}>
    <line x1={chart.left} y1={chart.top} x2={chart.left} y2={chart.height-chart.bottom} stroke="currentColor" opacity=".25"/>
    <line x1={chart.left} y1={chart.height-chart.bottom} x2={chart.width-12} y2={chart.height-chart.bottom} stroke="currentColor" opacity=".25"/>
    <text x={2} y={chart.top+4} fontSize={11} fill="currentColor">{format(chart.maxY)}</text>
    <text x={2} y={chart.height-chart.bottom} fontSize={11} fill="currentColor">{format(chart.minY)}</text>
    {chart.data.length>1?<polyline points={chart.poly} stroke="var(--light-accent, #158267)" strokeWidth="2.5" fill="none" strokeLinejoin="round" strokeLinecap="round"/>:null}
    {chart.data.length<=35&&chart.data.map((p,i)=>{const xy=chart.poly.split(' ')[i]?.split(',')||[];return <circle key={p.date} cx={Number(xy[0])} cy={Number(xy[1])} r={3.7} fill="var(--light-accent, #158267)"><title>{p.date}: {format(p.eur)}</title></circle>})}
    <text x={chart.left} y={chart.height-5} fontSize={11} fill="currentColor">{chart.data[0].date}</text>
    <text x={chart.width-12} y={chart.height-5} fontSize={11} fill="currentColor" textAnchor="end">{chart.data.at(-1)?.date}</text>
   </svg>
   <small>{points.length} erfasste Verkäufe · {chart.data.length} Tage mit Preisbeobachtungen</small>
  </>}
 </section>;
}
