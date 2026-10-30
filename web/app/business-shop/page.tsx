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
 const [design,setDesign]=useState<"classic"|"modern">("modern");
 useEffect(()=>{const stored=window.localStorage.getItem("cardyssey.businessShop.design");if(stored==="classic"||stored==="modern")setDesign(stored)},[]);
 const changeDesign=(next:"classic"|"modern")=>{setDesign(next);window.localStorage.setItem("cardyssey.businessShop.design",next)};
 useEffect(()=>{const abort=new AbortController();setSetId("");setDetail(null);setError("");setLoading(true);fetch("/api/sets?language="+encodeURIComponent(language),{signal:abort.signal,cache:"no-store"}).then(async res=>{if(!res.ok)throw Error("Katalog konnte nicht geladen werden");return res.json()}).then(v=>{if(!abort.signal.aborted)setSets(Array.isArray(v)?v:[])}).catch(e=>{if(!abort.signal.aborted)setError(String(e))}).finally(()=>{if(!abort.signal.aborted)setLoading(false)});return()=>abort.abort()},[language]);
 useEffect(()=>{const ctl=new AbortController();fetch("/api/shop/offers?language="+encodeURIComponent(language),{signal:ctl.signal,cache:"no-store"}).then(r=>r.ok?r.json():[]).then(v=>{if(!ctl.signal.aborted)setOffers(Array.isArray(v)?v:[])}).catch(()=>setOffers([]));return()=>ctl.abort()},[language]);
 useEffect(()=>{if(!setId)return;const abort=new AbortController();setLoading(true);setDetail(null);fetch("/api/sets/"+encodeURIComponent(setId)+"?language="+encodeURIComponent(language),{signal:abort.signal,cache:"no-store"}).then(async res=>{if(!res.ok)throw Error("Set nicht erreichbar");return res.json()}).then(v=>{if(!abort.signal.aborted)setDetail(v)}).catch(e=>{if(!abort.signal.aborted)setError(String(e))}).finally(()=>{if(!abort.signal.aborted)setLoading(false)});return()=>abort.abort()},[setId,language]);
 const match=useMemo(()=>query.trim().toLocaleLowerCase(),[query]);
 const visibleSets=sets.filter(s=>s.name.toLocaleLowerCase().includes(match));
 const visibleCards=(detail?.cards||[]).filter(c=>(c.name+" "+(c.localId||"")).toLocaleLowerCase().includes(match));
 return <div className={"businessShop "+(design==="modern"?"businessShopModern":"businessShopClassic")}><header className="businessShopHeader"><Link href="/" className="businessShopBrand"><img src="/cardyssey-emblem-gold.png" alt="" width="44" height="44"/> CARDYSSEY <span>STORE</span></Link><nav><a href="#produkte">Einzelkarten</a><a href="#produkte">Sets</a><div className="businessShopDesignSwitch" aria-label="Shopdesign"><button type="button" onClick={()=>changeDesign("classic")} aria-pressed={design==="classic"}>Klassisch</button><button type="button" onClick={()=>changeDesign("modern")} aria-pressed={design==="modern"}>Modern</button></div><Link href="https://cardyssey.de/impressum">Impressum</Link></nav></header><main className="businessShopMain" id="produkte">
 {design==="modern"&&<div className="businessShopHero">
 <div className="businessShopHeroContent"><span className="businessShopHeroEyebrow">CARDYSSEY · TRADING CARD STORE</span>
 <h1>Deine nächste <em>Lieblingskarte.</em></h1>
 <p>Entdecke Pokémon-Sammelkarten, finde deine fehlenden Karten und stöbere durch unsere Sets. Alle angebotenen Karten stammen aus unserem eigenen Warenbestand.</p>
 <a className="businessShopHeroAction" href="#shop-katalog">Sets entdecken <span aria-hidden="true">→</span></a>
 <div className="businessShopHeroStats"><span><strong>{sets.length}</strong> Sets im Katalog</span><span><strong>{offers.length}</strong> aktuelle Verkaufsangebote</span></div></div>
 <div className="businessShopHeroArtwork" aria-hidden="true"><div className="businessShopHeroCard businessShopHeroCardBack"></div><div className="businessShopHeroCard businessShopHeroCardFront"><img src="/cardyssey-emblem-gold.png" alt=""/></div><span className="businessShopHeroHalo"></span></div></div>}
 <div id="shop-katalog" className="businessShopSectionHeading"><span>{design==="modern"?"ENTDECKE DEINE KARTEN":"KARTENKATALOG"}</span><h2>Nach Sets stöbern</h2><p>Wähle eine Erweiterung aus oder suche gezielt nach einer Karte.</p></div>
 <section className="pageIntro" style={{display:design==="modern"?"none":undefined}}><div><span className="eyebrowText">Cardyssey · Gewerblicher Webshop</span><h1>Cardyssey Webshop · Einzelkarten</h1><p>Hier werden ausschließlich Angebote aus dem gewerblichen Cardyssey-Warenbestand angezeigt. Das Nutzerinventar bleibt unabhängig. Bestellungen und Zahlungen sind derzeit deaktiviert.</p></div></section>
 <div style={{display:"flex",gap:12,flexWrap:"wrap",marginBottom:22}}>
  <label>Sprache <select value={language} onChange={e=>setLanguage(e.target.value)}>{languages.map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label>
  <label>Karte oder Set suchen <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Name / Nummer"/></label>
 </div>
 {error&&<p role="alert" className="statusPanel">{error}</p>}
 {loading&&<p role="status">Katalog wird geladen …</p>}
 {detail?<><button className="ghostButton" type="button" onClick={()=>{setSetId("");setDetail(null);setQuery("")}}>← Alle Sets</button><h2>{detail.name}</h2><p>{visibleCards.length} Karten</p><section className="cardGrid">{visibleCards.map(c=><article key={c.id} className="cardTile">{c.imageBase&&<img src={c.imageBase.replace(/\/$/,"")+"/high.webp"} alt={c.name} loading="lazy" style={{height:200,width:"100%",objectFit:"contain"}}/>}<strong>{c.name}</strong><p>{c.localId||c.id}</p>{offers.filter(o=>o.card_id===c.id&&o.set_id===setId&&o.language===language).length ? offers.filter(o=>o.card_id===c.id&&o.set_id===setId&&o.language===language).map(o=><p key={o.id}>{o.variant} · {o.condition} · {(o.price_minor/100).toLocaleString("de-DE",{style:"currency",currency:"EUR"})} · {o.available_quantity} Stück <small>(Bestellung noch deaktiviert)</small></p>) : <span>Kein Verkaufsangebot vorhanden</span>}</article>)}</section></>
 :<><h2 className="businessShopCatalogTitle">Alle Sets</h2><section className="cardGrid">{visibleSets.map(s=><button key={s.id} type="button" className="cardTile" style={{textAlign:"left",cursor:"pointer"}} onClick={()=>{setSetId(s.id);setQuery("")}}><span className="businessShopSetIcon" aria-hidden="true">✦</span><strong>{s.name}</strong><span className="businessShopSetCount">{s.officialCount??s.totalCount??"–"} Karten <span aria-hidden="true">→</span></span></button>)}</section></>}
 </main><footer className="businessShopFooter">Cardyssey Gewerbe-Webshop · Kein Checkout aktiviert · <Link href="https://cardyssey.de/datenschutz">Datenschutz</Link> · <Link href="https://cardyssey.de/impressum">Impressum</Link></footer></div>;
}
