"use client";
import {useEffect,useMemo,useState} from "react";
import Link from "next/link";
import "./business-shop.css";
type SetItem={id:string;name:string;officialCount?:number;totalCount?:number};
type CardItem={id:string;name:string;localId?:string;imageBase?:string|null};
type SetDetail={name:string;cards:CardItem[]};
type Offer={id:number;card_id:string;set_id:string;language:string;variant:string;condition:string;price_minor:number;available_quantity:number};
const languages=[["de","Deutsch"],["en","Englisch"],["ja","Japanisch"],["ko","Koreanisch"],["zh-cn","Chinesisch (vereinfacht)"],["zh-tw","Chinesisch (traditionell)"]];
export default function ShopPage(){
 const [language,setLanguage]=useState("de"),[setId,setSetId]=useState(""),[query,setQuery]=useState(""),[error,setError]=useState("");
 const [sets,setSets]=useState<SetItem[]>([]),[detail,setDetail]=useState<SetDetail|null>(null),[loading,setLoading]=useState(true);
 const [offers,setOffers]=useState<Offer[]>([]);
 useEffect(()=>{const abort=new AbortController();setSetId("");setDetail(null);setError("");setLoading(true);fetch("/api/sets?language="+encodeURIComponent(language),{signal:abort.signal,cache:"no-store"}).then(async res=>{if(!res.ok)throw Error("Katalog konnte nicht geladen werden");return res.json()}).then(v=>{if(!abort.signal.aborted)setSets(Array.isArray(v)?v:[])}).catch(e=>{if(!abort.signal.aborted)setError(String(e))}).finally(()=>{if(!abort.signal.aborted)setLoading(false)});return()=>abort.abort()},[language]);
 useEffect(()=>{const ctl=new AbortController();fetch("/api/shop/offers?language="+encodeURIComponent(language),{signal:ctl.signal,cache:"no-store"}).then(r=>r.ok?r.json():[]).then(v=>{if(!ctl.signal.aborted)setOffers(Array.isArray(v)?v:[])}).catch(()=>setOffers([]));return()=>ctl.abort()},[language]);
 useEffect(()=>{if(!setId)return;const abort=new AbortController();setLoading(true);setDetail(null);fetch("/api/sets/"+encodeURIComponent(setId)+"?language="+encodeURIComponent(language),{signal:abort.signal,cache:"no-store"}).then(async res=>{if(!res.ok)throw Error("Set nicht erreichbar");return res.json()}).then(v=>{if(!abort.signal.aborted)setDetail(v)}).catch(e=>{if(!abort.signal.aborted)setError(String(e))}).finally(()=>{if(!abort.signal.aborted)setLoading(false)});return()=>abort.abort()},[setId,language]);
 const match=useMemo(()=>query.trim().toLocaleLowerCase(),[query]);
 const visibleSets=sets.filter(s=>s.name.toLocaleLowerCase().includes(match));
 const visibleCards=(detail?.cards||[]).filter(c=>(c.name+" "+(c.localId||"")).toLocaleLowerCase().includes(match));
 return <div className="businessShop"><header className="businessShopHeader"><Link href="/" className="businessShopBrand"><img src="/cardyssey-emblem-gold.png" alt="" width="44" height="44"/> CARDYSSEY <span>STORE</span></Link><nav><a href="#produkte">Einzelkarten</a><a href="#produkte">Sets</a><Link href="https://cardyssey.de/impressum">Impressum</Link></nav></header><main className="businessShopMain" id="produkte">
 <section className="pageIntro"><div><span className="eyebrowText">Cardyssey · Gewerblicher Webshop</span><h1>Cardyssey Webshop · Einzelkarten</h1><p>Hier werden ausschließlich Angebote aus dem gewerblichen Cardyssey-Warenbestand angezeigt. Das Nutzerinventar bleibt unabhängig. Bestellungen und Zahlungen sind derzeit deaktiviert.</p></div></section>
 <div style={{display:"flex",gap:12,flexWrap:"wrap",marginBottom:22}}>
  <label>Sprache <select value={language} onChange={e=>setLanguage(e.target.value)}>{languages.map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label>
  <label>Karte oder Set suchen <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Name / Nummer"/></label>
 </div>
 {error&&<p role="alert" className="statusPanel">{error}</p>}
 {loading&&<p role="status">Katalog wird geladen …</p>}
 {detail?<><button className="ghostButton" type="button" onClick={()=>{setSetId("");setDetail(null);setQuery("")}}>← Alle Sets</button><h2>{detail.name}</h2><p>{visibleCards.length} Karten</p><section className="cardGrid">{visibleCards.map(c=><article key={c.id} className="cardTile">{c.imageBase&&<img src={c.imageBase.replace(/\/$/,"")+"/high.webp"} alt={c.name} loading="lazy" style={{height:200,width:"100%",objectFit:"contain"}}/>}<strong>{c.name}</strong><p>{c.localId||c.id}</p>{offers.filter(o=>o.card_id===c.id&&o.set_id===setId&&o.language===language).length ? offers.filter(o=>o.card_id===c.id&&o.set_id===setId&&o.language===language).map(o=><p key={o.id}>{o.variant} · {o.condition} · {(o.price_minor/100).toLocaleString("de-DE",{style:"currency",currency:"EUR"})} · {o.available_quantity} Stück <small>(Bestellung noch deaktiviert)</small></p>) : <span>Kein Verkaufsangebot vorhanden</span>}</article>)}</section></>
 :<><h2>Alle Sets</h2><section className="cardGrid">{visibleSets.map(s=><button key={s.id} type="button" className="cardTile" style={{textAlign:"left",cursor:"pointer"}} onClick={()=>{setSetId(s.id);setQuery("")}}><strong>{s.name}</strong><span>{s.officialCount??s.totalCount??"–"} Karten</span></button>)}</section></>}
 </main><footer className="businessShopFooter">Cardyssey Gewerbe-Webshop · Kein Checkout aktiviert · <Link href="https://cardyssey.de/datenschutz">Datenschutz</Link> · <Link href="https://cardyssey.de/impressum">Impressum</Link></footer></div>;
}
