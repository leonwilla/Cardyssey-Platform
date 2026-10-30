"use client";
import {useEffect,useMemo,useState} from "react";
import {AppShell} from "@/components/AppShell";
type SetItem={id:string;name:string;officialCount?:number;totalCount?:number};
type CardItem={id:string;name:string;localId?:string;imageBase?:string|null};
type SetDetail={name:string;cards:CardItem[]};
const languages=[["de","Deutsch"],["en","Englisch"],["ja","Japanisch"],["ko","Koreanisch"],["zh-cn","Chinesisch (vereinfacht)"],["zh-tw","Chinesisch (traditionell)"]];
export default function ShopPage(){
 const [language,setLanguage]=useState("de"),[setId,setSetId]=useState(""),[query,setQuery]=useState(""),[error,setError]=useState("");
 const [sets,setSets]=useState<SetItem[]>([]),[detail,setDetail]=useState<SetDetail|null>(null),[loading,setLoading]=useState(true);
 useEffect(()=>{const abort=new AbortController();setSetId("");setDetail(null);setError("");setLoading(true);fetch("/api/sets?language="+encodeURIComponent(language),{signal:abort.signal,cache:"no-store"}).then(async res=>{if(!res.ok)throw Error("Katalog konnte nicht geladen werden");return res.json()}).then(v=>{if(!abort.signal.aborted)setSets(Array.isArray(v)?v:[])}).catch(e=>{if(!abort.signal.aborted)setError(String(e))}).finally(()=>{if(!abort.signal.aborted)setLoading(false)});return()=>abort.abort()},[language]);
 useEffect(()=>{if(!setId)return;const abort=new AbortController();setLoading(true);setDetail(null);fetch("/api/sets/"+encodeURIComponent(setId)+"?language="+encodeURIComponent(language),{signal:abort.signal,cache:"no-store"}).then(async res=>{if(!res.ok)throw Error("Set nicht erreichbar");return res.json()}).then(v=>{if(!abort.signal.aborted)setDetail(v)}).catch(e=>{if(!abort.signal.aborted)setError(String(e))}).finally(()=>{if(!abort.signal.aborted)setLoading(false)});return()=>abort.abort()},[setId,language]);
 const match=useMemo(()=>query.trim().toLocaleLowerCase(),[query]);
 const visibleSets=sets.filter(s=>s.name.toLocaleLowerCase().includes(match));
 const visibleCards=(detail?.cards||[]).filter(c=>(c.name+" "+(c.localId||"")).toLocaleLowerCase().includes(match));
 return <AppShell active="/shop">
 <section className="pageIntro"><div><span className="eyebrowText">Cardyssey · Eigener Shop</span><h1>Karten & Sammlerstücke</h1><p>Unser neuer Kartenkatalog ist direkt mit Cardyssey verbunden – ohne WordPress und WooCommerce. Verkauf und Bestellungen bleiben bis zur geprüften Freigabe deaktiviert.</p></div></section>
 <div style={{display:"flex",gap:12,flexWrap:"wrap",marginBottom:22}}>
  <label>Sprache <select value={language} onChange={e=>setLanguage(e.target.value)}>{languages.map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label>
  <label>Karte oder Set suchen <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Name / Nummer"/></label>
 </div>
 {error&&<p role="alert" className="statusPanel">{error}</p>}
 {loading&&<p role="status">Katalog wird geladen …</p>}
 {detail?<><button className="ghostButton" type="button" onClick={()=>{setSetId("");setDetail(null);setQuery("")}}>← Alle Sets</button><h2>{detail.name}</h2><p>{visibleCards.length} Karten</p><section className="cardGrid">{visibleCards.map(c=><article key={c.id} className="cardTile">{c.imageBase&&<img src={c.imageBase.replace(/\/$/,"")+"/high.webp"} alt={c.name} loading="lazy" style={{height:200,width:"100%",objectFit:"contain"}}/>}<strong>{c.name}</strong><p>{c.localId||c.id}</p><span>Kein Verkaufsangebot vorhanden</span></article>)}</section></>
 :<><h2>Alle Sets</h2><section className="cardGrid">{visibleSets.map(s=><button key={s.id} type="button" className="cardTile" style={{textAlign:"left",cursor:"pointer"}} onClick={()=>{setSetId(s.id);setQuery("")}}><strong>{s.name}</strong><span>{s.officialCount??s.totalCount??"–"} Karten</span></button>)}</section></>}
 </AppShell>;
}
