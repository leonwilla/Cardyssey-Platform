"use client";
import {useEffect,useMemo,useState} from "react";
import Link from "next/link";
import "./business-shop.css";
type SetItem={id:string;name:string;officialCount?:number;totalCount?:number;logo?:string|null;symbol?:string|null};
type CardItem={id:string;name:string;localId?:string;imageBase?:string|null};
type SetDetail={name:string;cards:CardItem[]};
type Offer={id:number;card_id:string;set_id:string;language:string;variant:string;condition:string;price_minor:number;available_quantity:number;title?:string};
function SetArtwork({setId,language,cardId}:{setId:string;language:string;cardId?:string}){
 const [image,setImage]=useState<string|null>(null);
 useEffect(()=>{const ctl=new AbortController();setImage(null);fetch("/api/sets/"+encodeURIComponent(setId)+"?language="+encodeURIComponent(language),{signal:ctl.signal,cache:"force-cache"}).then(r=>r.ok?r.json():null).then(data=>{if(ctl.signal.aborted)return;const cards=Array.isArray(data?.cards)?data.cards:[];const card=cards.find((c:{id:string;imageBase?:string|null})=>(!cardId||c.id===cardId)&&!!c.imageBase);setImage(card?.imageBase?card.imageBase.replace(/\\/$/,"")+"/high.webp":null)}).catch(()=>{});return()=>ctl.abort()},[setId,language,cardId]);
 return image?<img className="shopSetPreviewImage" src={image} alt="" loading="lazy"/>:<span className="shopSetMark" aria-hidden="true">✦</span>;
}
const languages=[["de","Deutsch"],["en","Englisch"],["ja","Japanisch"],["ko","Koreanisch"],["zh-cn","Chinesisch (vereinfacht)"],["zh-tw","Chinesisch (traditionell)"]];
export default function ShopPage(){
 const [language,setLanguage]=useState("de"),[setId,setSetId]=useState(""),[query,setQuery]=useState(""),[error,setError]=useState("");
 const [sets,setSets]=useState<SetItem[]>([]),[detail,setDetail]=useState<SetDetail|null>(null),[loading,setLoading]=useState(true);
 const [detailLoading,setDetailLoading]=useState(false);
 const [offers,setOffers]=useState<Offer[]>([]);
 const [mode,setMode]=useState<"sets"|"listings">("sets"),[onlyStock,setOnlyStock]=useState(true),[sort,setSort]=useState("name");
 const [design,setDesign]=useState<"classic"|"modern">("modern");
 useEffect(()=>{const stored=window.localStorage.getItem("cardyssey.businessShop.design");if(stored==="classic"||stored==="modern")setDesign(stored)},[]);
 const changeDesign=(next:"classic"|"modern")=>{setDesign(next);window.localStorage.setItem("cardyssey.businessShop.design",next)};
 useEffect(()=>{const abort=new AbortController();setSetId("");setDetail(null);setDetailLoading(false);setError("");setLoading(true);fetch("/api/sets?language="+encodeURIComponent(language),{signal:abort.signal,cache:"no-store"}).then(async res=>{if(!res.ok)throw Error("Katalog konnte nicht geladen werden");return res.json()}).then(v=>{if(!abort.signal.aborted)setSets(Array.isArray(v)?v:[])}).catch(e=>{if(!abort.signal.aborted)setError(String(e))}).finally(()=>{if(!abort.signal.aborted)setLoading(false)});return()=>abort.abort()},[language]);
 useEffect(()=>{const ctl=new AbortController();fetch("/api/shop/offers?language="+encodeURIComponent(language),{signal:ctl.signal,cache:"no-store"}).then(r=>r.ok?r.json():[]).then(v=>{if(!ctl.signal.aborted)setOffers(Array.isArray(v)?v:[])}).catch(()=>setOffers([]));return()=>ctl.abort()},[language]);
 useEffect(()=>{if(!setId)return;const abort=new AbortController();setDetailLoading(true);setDetail(null);fetch("/api/sets/"+encodeURIComponent(setId)+"?language="+encodeURIComponent(language),{signal:abort.signal,cache:"no-store"}).then(async res=>{if(!res.ok)throw Error("Set nicht erreichbar");return res.json()}).then(v=>{if(!abort.signal.aborted)setDetail(v)}).catch(e=>{if(!abort.signal.aborted)setError(String(e))}).finally(()=>{if(!abort.signal.aborted)setDetailLoading(false)});return()=>abort.abort()},[setId,language]);
 const match=useMemo(()=>query.trim().toLocaleLowerCase(),[query]);
 const offeredSetIds=new Set(offers.filter(o=>o.available_quantity>0).map(o=>o.set_id));
 const visibleSets=sets.filter(s=>s.name.toLocaleLowerCase().includes(match)&&(!onlyStock||offeredSetIds.has(s.id))).sort((a,b)=>sort==="count"?(b.officialCount??b.totalCount??0)-(a.officialCount??a.totalCount??0):a.name.localeCompare(b.name,"de"));
 const visibleCards=(detail?.cards||[]).filter(c=>(c.name+" "+(c.localId||"")).toLocaleLowerCase().includes(match)&&(!onlyStock||offers.some(o=>o.card_id===c.id&&o.set_id===setId)));
 const visibleOffers=offers.filter(o=>(o.title+" "+o.card_id+" "+(sets.find(s=>s.id===o.set_id)?.name||"")).toLocaleLowerCase().includes(match)).sort((a,b)=>sort==="price-asc"?a.price_minor-b.price_minor:sort==="price-desc"?b.price_minor-a.price_minor:(a.title||"").localeCompare(b.title||"","de"));
 const showSet=(id:string)=>{setSetId(id);setMode("sets");setQuery("");document.getElementById("shop-katalog")?.scrollIntoView({behavior:"smooth"})};
 return <div className={"businessShop "+(design==="modern"?"businessShopModern":"businessShopClassic")}><header className="businessShopHeader"><Link href="/" className="businessShopBrand"><img src="/cardyssey-emblem-gold.png" alt="" width="44" height="44"/> CARDYSSEY <span>STORE</span></Link><nav><a href="#shop-katalog" onClick={()=>{setMode("listings");setSetId("")}}>Einzelkarten</a><a href="#shop-katalog" onClick={()=>{setMode("sets");setSetId("")}}>Sets</a><div className="businessShopDesignSwitch" aria-label="Shopdesign"><button type="button" onClick={()=>changeDesign("classic")} aria-pressed={design==="classic"}>Klassisch</button><button type="button" onClick={()=>changeDesign("modern")} aria-pressed={design==="modern"}>Modern</button></div><Link href="https://cardyssey.de/impressum">Impressum</Link></nav></header><main className="businessShopMain" id="produkte">
 {design==="modern"&&<div className="businessShopHero">
 <div className="businessShopHeroContent"><span className="businessShopHeroEyebrow">CARDYSSEY · TRADING CARD STORE</span>
 <h1>Deine nächste <em>Lieblingskarte.</em></h1>
 <p>Entdecke Pokémon-Sammelkarten, finde deine fehlenden Karten und stöbere durch unsere Sets. Alle angebotenen Karten stammen aus unserem eigenen Warenbestand.</p>
 <a className="businessShopHeroAction" href="#shop-katalog">Sets entdecken <span aria-hidden="true">→</span></a>
 <div className="businessShopHeroStats"><span><strong>{sets.length}</strong> Sets im Katalog</span><span><strong>{offers.length}</strong> aktuelle Verkaufsangebote</span></div></div>
 <div className="businessShopHeroArtwork" aria-hidden="true"><div className="businessShopHeroCard businessShopHeroCardBack"></div><div className="businessShopHeroCard businessShopHeroCardFront"><img src="/cardyssey-emblem-gold.png" alt=""/></div><span className="businessShopHeroHalo"></span></div></div>}
 <div id="shop-katalog" className="businessShopSectionHeading"><span>DEIN KARTENKATALOG</span><h2>{mode==="listings"?"Verfügbare Einzelkarten":setId?(detail?.name||"Set entdecken"):"Erweiterungen entdecken"}</h2><p>Wie bei einem TCG-Marktplatz: nach Sets suchen, verfügbare Karten finden und Angebote vergleichen.</p></div>
 <section className="pageIntro" style={{display:design==="modern"?"none":undefined}}><div><span className="eyebrowText">Cardyssey · Gewerblicher Webshop</span><h1>Cardyssey Webshop · Einzelkarten</h1><p>Hier werden ausschließlich Angebote aus dem gewerblichen Cardyssey-Warenbestand angezeigt. Das Nutzerinventar bleibt unabhängig. Bestellungen und Zahlungen sind derzeit deaktiviert.</p></div></section>

 <div className="shopBrowse">
  <aside className="shopBrowseSidebar">
   <h3>Katalog durchsuchen</h3>
   <div className="shopBrowseTabs"><button aria-pressed={mode==="sets"} onClick={()=>{setMode("sets");setSetId("")}}>Erweiterungen</button><button aria-pressed={mode==="listings"} onClick={()=>{setMode("listings");setSetId("")}}>Verkaufsangebote <span>{offers.length}</span></button></div>
   <label>Sprache<select value={language} onChange={e=>setLanguage(e.target.value)}>{languages.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
   <label>Suche<input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Kartenname, Nummer, Set …"/></label>
   {mode==="sets"&&<label className="shopCheck"><input type="checkbox" checked={onlyStock} onChange={e=>setOnlyStock(e.target.checked)}/> Nur Sets mit Angeboten</label>}
   <label>Sortierung<select value={sort} onChange={e=>setSort(e.target.value)}>{mode==="listings"?<><option value="name">Name A–Z</option><option value="price-asc">Preis aufsteigend</option><option value="price-desc">Preis absteigend</option></>:<><option value="name">Setname A–Z</option><option value="count">Meiste Karten</option></>}</select></label>
   <div className="shopSidebarNote"><strong>Cardyssey Store</strong><p>Hier findest du ausschließlich gewerbliche Angebote. Der Nutzer-Marktplatz bleibt getrennt.</p></div>
  </aside>
  <section className="shopBrowseContent">
   <div className="shopBrowseTop"><div><span className="shopBrowseEyebrow">POKÉMON TCG</span><h3>{mode==="listings"?"Unsere Einzelkarten":setId?detail?.name||"Karten laden":"Alle Erweiterungen"}</h3><p>{mode==="listings"?visibleOffers.length+" verfügbare Angebote":setId?visibleCards.length+" Karten":visibleSets.length+" Sets"}</p></div>{setId&&<button className="shopBack" onClick={()=>{setSetId("");setQuery("")}}>← Alle Sets</button>}</div>
   {error&&<p role="alert" className="shopEmpty">{error}</p>}
   {(loading||detailLoading)&&<p role="status" className="shopEmpty">Katalog wird geladen …</p>}
   {!loading&&mode==="listings"&&(visibleOffers.length?<div className="shopProductGrid">{visibleOffers.map(offer=><article className="shopProduct" key={offer.id}><div className="shopProductArt"><SetArtwork setId={offer.set_id} language={language} cardId={offer.card_id}/></div><div className="shopProductInfo"><span className="shopProductMeta">{sets.find(s=>s.id===offer.set_id)?.name||offer.set_id} · {language.toUpperCase()}</span><h4>{offer.title||offer.card_id}</h4><p>{offer.variant} · {offer.condition}</p><div className="shopProductBottom"><strong>{(offer.price_minor/100).toLocaleString("de-DE",{style:"currency",currency:"EUR"})}</strong><small>{offer.available_quantity} verfügbar</small></div></div></article>)}</div>:<div className="shopEmpty">Aktuell sind keine veröffentlichten Karten verfügbar. Neue Angebote werden nach Freigabe durch die Shopverwaltung hier angezeigt.</div>)}
   {!loading&&mode==="sets"&&!setId&&(visibleSets.length?<div className="shopSetGrid">{visibleSets.map(set=><button type="button" key={set.id} className="shopSetTile" onClick={()=>showSet(set.id)}><div className="shopSetArtwork"><SetArtwork setId={set.id} language={language}/><span className="shopSetCount">{set.officialCount??set.totalCount??"–"} Karten</span></div><div className="shopSetDetails"><strong>{set.name}</strong><span>{offeredSetIds.has(set.id)?"Verkaufsangebote vorhanden":"Katalog ansehen"} <span aria-hidden="true">→</span></span></div></button>)}</div>:<div className="shopEmpty">{onlyStock?"Zurzeit sind keine gewerblichen Karten aus diesem Bereich veröffentlicht. Sobald du Angebote im Admin freigibst, erscheinen die passenden Sets hier automatisch.":"Keine passenden Sets gefunden."}</div>)}
   {mode==="sets"&&setId&&!detailLoading&&detail&&<div className="shopProductGrid">{visibleCards.map(card=>{const listed=offers.filter(offer=>offer.card_id===card.id&&offer.set_id===setId);const image=card.imageBase?card.imageBase.replace(/\/$/,"")+"/high.webp":null;return <article className="shopProduct" key={card.id}><div className="shopProductArt">{image?<img loading="lazy" src={image} alt={card.name}/>:<span className="shopProductPlaceholder">✦</span>}</div><div className="shopProductInfo"><span className="shopProductMeta">{detail.name} · {card.localId||card.id}</span><h4>{card.name}</h4>{listed.length?listed.map(offer=><div key={offer.id} className="shopListingLine"><span>{offer.variant} · {offer.condition}</span><strong>{(offer.price_minor/100).toLocaleString("de-DE",{style:"currency",currency:"EUR"})}</strong><small>{offer.available_quantity} Stück verfügbar</small></div>):<p className="shopNotAvailable">Aktuell nicht auf Lager</p>}</div></article>})}</div>}
  </section>
 </div>
 </main><footer className="businessShopFooter">Cardyssey Gewerbe-Webshop · Kein Checkout aktiviert · <Link href="https://cardyssey.de/datenschutz">Datenschutz</Link> · <Link href="https://cardyssey.de/impressum">Impressum</Link></footer></div>;
}
