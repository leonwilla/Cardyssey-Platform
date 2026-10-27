"use client";
import {useEffect,useMemo,useState} from "react";
import {useRouter} from "next/navigation";
import {AppShell} from "@/components/AppShell";
import type {User} from "@/lib/types";

type SetItem={id:string;name:string;officialCount?:number;totalCount?:number};
type Card={id:string;name:string;localId:string;imageBase?:string|null};
type Detail={id:string;name:string;cards:Card[];officialCount?:number};
type Listing={card:Card;setName:string;setId:string;language:string;variant:string;condition:string;quantity:number;price:string;enabled:boolean;photoUrl:string};
const languages=[["de","Deutsch"],["en","Englisch"],["ja","Japanisch"],["ko","Koreanisch"],["zh-cn","Chinesisch (vereinfacht)"],["zh-tw","Chinesisch (traditionell)"]];
const variants=["Normal","Holo","Reverse Holo","Full Art","Illustration Rare","Special Illustration Rare","Promo","Sonstige"];
const conditions=["Near Mint","Excellent","Good","Light Played","Played","Poor"];
const csv=(v:unknown)=>'"'+String(v??"").replace(/"/g,'""').replace(/\r?\n/g," ")+'"';
const escSku=(v:string)=>v.normalize("NFKD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]/gi,"-").replace(/-+/g,"-").slice(0,65).toUpperCase();
export default function ShopCatalog(){
 const router=useRouter();
 const [allowed,setAllowed]=useState(false),[loading,setLoading]=useState(true),[error,setError]=useState("");
 const [language,setLanguage]=useState("de"),[sets,setSets]=useState<SetItem[]>([]),[setId,setSetId]=useState(""),[details,setDetails]=useState<Detail|null>(null),[search,setSearch]=useState("");
 const [selected,setSelected]=useState<Record<string,Listing>>({});
 useEffect(()=>{fetch("/api/auth/me",{cache:"no-store"}).then(async r=>{if(r.status===401){router.replace("/login");return;}if(!r.ok)throw Error("Loginstatus nicht verfügbar");const u=await r.json() as User;if(u.role!=="FOUNDER"&&u.role!=="ADMIN"&&u.canAdmin!==true){router.replace("/account");return;}setAllowed(true)}).catch(e=>setError(String(e))).finally(()=>setLoading(false))},[router]);
 useEffect(()=>{if(!allowed)return;const ctl=new AbortController();setDetails(null);setSetId("");setError("");fetch("/api/sets?language="+encodeURIComponent(language),{signal:ctl.signal,cache:"no-store"}).then(async r=>{if(!r.ok)throw Error("Sets konnten nicht geladen werden");const d=await r.json();if(!ctl.signal.aborted)setSets(Array.isArray(d)?d:[])}).catch(e=>{if(!ctl.signal.aborted)setError(String(e))});return()=>ctl.abort()},[allowed,language]);
 useEffect(()=>{if(!setId||!allowed)return;const ctl=new AbortController();setDetails(null);fetch("/api/sets/"+encodeURIComponent(setId)+"?language="+encodeURIComponent(language),{signal:ctl.signal,cache:"no-store"}).then(async r=>{if(!r.ok)throw Error("Set konnte nicht geladen werden");const d=await r.json() as Detail;if(!ctl.signal.aborted)setDetails(d)}).catch(e=>{if(!ctl.signal.aborted)setError(String(e))});return()=>ctl.abort()},[setId,language,allowed]);
 const key=(card:Card)=>[language,setId,card.id].join("|");
 const select=(card:Card)=>{const k=key(card);setSelected(old=>old[k]?Object.fromEntries(Object.entries(old).filter(([id])=>id!==k)):{...old,[k]:{card,setId,setName:details?.name||setId,language,variant:"Normal",condition:"Near Mint",quantity:0,price:"",enabled:false,photoUrl:""}})};
 const addCondition=(id:string)=>{const source=selected[id];if(!source)return;const available=conditions.find(c=>!Object.values(selected).some(x=>x.card.id===source.card.id&&x.setId===source.setId&&x.language===source.language&&x.variant===source.variant&&x.condition===c));if(!available){setError("Für diese Variante sind bereits alle Zustände ausgewählt.");return;}const next=id+"|"+source.variant+"|"+available;setSelected(old=>({...old,[next]:{...source,condition:available,quantity:0,price:"",enabled:false}}))};
 const change=(id:string,patch:Partial<Listing>)=>setSelected(old=>({...old,[id]:{...old[id],...patch}}));
 const filtered=useMemo(()=>details?.cards.filter(c=>[c.name,c.localId,c.id].join(" ").toLowerCase().includes(search.toLowerCase()))??[],[details,search]);
 const entries=Object.entries(selected);
 const download=()=>{setError("");if(!entries.length){setError("Bitte Karten auswählen.");return;}
  const headers=["Type","SKU","Name","Published","Is featured?","Visibility in catalog","Short description","Description","In stock?","Stock","Backorders allowed?","Sold individually?","Regular price","Categories","Images","Attribute 1 name","Attribute 1 value(s)","Attribute 1 visible","Attribute 1 global","Attribute 2 name","Attribute 2 value(s)","Attribute 2 visible","Attribute 2 global","Attribute 3 name","Attribute 3 value(s)","Attribute 3 visible","Attribute 3 global"];
  const rows:string[]=[];
  const keys=new Set<string>();
  for(const [id,l] of entries){
    const amount=Number(l.price.replace(",","."));if(l.photoUrl && !/^https:\\/\\//i.test(l.photoUrl.trim())){setError("Eigene Fotos müssen eine HTTPS-Bildadresse haben.");return;}if(l.enabled&&(!Number.isFinite(amount)||amount<=0||!Number.isInteger(l.quantity)||l.quantity<1)){setError("Für freigegebene Karten bitte positiven Preis und Bestand ab 1 festlegen.");return;}
    const title=[l.card.name,l.card.localId,l.setName,l.variant,l.condition].join(" · ");
    const image=l.photoUrl.trim() || (l.card.imageBase?l.card.imageBase.replace(/\/$/,"")+"/high.webp":"");
    const sku="CDY-"+escSku(l.language+"-"+l.setId+"-"+l.card.id+"-"+l.variant+"-"+l.condition);if(keys.has(sku)){setError("Doppelte Kartenvariante/Zustand erkannt. Bitte pro Kombination nur einen Eintrag exportieren.");return;}keys.add(sku);
    const values=["simple",sku,title,"0","0","visible",l.setName+" | "+l.card.localId+" | "+l.language+" | "+l.variant+" | "+l.condition,(l.photoUrl?"Originalfoto dieses Exemplars. ":"Referenzbild: Das Kartenmotiv zeigt nicht den tatsächlichen Zustand des angebotenen Exemplars. ")+"Zustand: "+l.condition+".",l.enabled?"1":"0",l.enabled?String(l.quantity):"0","0","0",l.enabled?amount.toFixed(2):"","Einzelkarten, Einzelkarten > "+l.setName,image,"Sprache",languages.find(x=>x[0]===l.language)?.[1]||l.language,"1","0","Variante",l.variant,"1","0","Zustand",l.condition,"1","0"];
    rows.push(values.map(csv).join(","));
  }
  const output="\uFEFF"+[headers.map(csv).join(","),...rows].join("\r\n")+"\r\n";const u=URL.createObjectURL(new Blob([output],{type:"text/csv;charset=utf-8"}));const a=document.createElement("a");a.href=u;a.download="cardyssey-shop-katalog.csv";a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);
 };
 const fieldStyle={minHeight:40,border:"1px solid var(--border)",borderRadius:10,padding:"6px 10px",background:"var(--navy-card)",color:"var(--text)",width:"100%"} as const;
 return <AppShell active="/admin"><section className="pageIntro"><div><span className="eyebrowText">Shop-Verwaltung</span><h1>Kartenkatalog → Shop</h1><p>Set auswählen, Karte finden, Bestand und Verkaufspreis festlegen. Nicht freigegebene Karten bleiben unverkäuflich.</p></div></section>
 {!allowed?<div className="statusPanel">{loading?"Zugriff wird geprüft …":error||"Keine Berechtigung"}</div>:<>
 <div className="statusPanel"><strong>Sicherer Entwurfsmodus:</strong> Der Export legt alle Karten zunächst als WooCommerce-Entwürfe an. Bei nicht freigegebenen Karten werden Bestand 0 und „Nicht vorrätig“ gesetzt. Eine freigegebene Karte musst du nach dem Import in WooCommerce noch veröffentlichen. So wird nichts unbeabsichtigt verkauft.</div>
 <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(220px,1fr))",gap:14,margin:"22px 0"}}>
 <label>Sprache<select style={fieldStyle} value={language} onChange={e=>setLanguage(e.target.value)}>{languages.map(([id,name])=><option key={id} value={id}>{name}</option>)}</select></label>
 <label>Erweiterung<select style={fieldStyle} value={setId} onChange={e=>{setSetId(e.target.value);setSearch("")}}><option value="">Set auswählen</option>{sets.map(s=><option key={s.id} value={s.id}>{s.name} ({s.officialCount||s.totalCount||"–"})</option>)}</select></label>
 <label>Karte suchen<input style={fieldStyle} value={search} onChange={e=>setSearch(e.target.value)} placeholder="Name oder 010" /></label>
 </div>
 {error&&<div role="alert" className="statusPanel errorPanel">{error}</div>}
 <div className="cardGrid">{filtered.map(card=>{const id=key(card),chosen=!!selected[id];return <button type="button" key={card.id} onClick={()=>select(card)} className="cardTile interactiveCard" style={{textAlign:"left",outline:chosen?"2px solid var(--cyan)":undefined}}>
 <div className="cardImageWrap">{card.imageBase?<img loading="lazy" className="cardImage" src={card.imageBase.replace(/\/$/,"")+"/high.webp"} alt={card.name}/>:<span>Kein Bild</span>}</div><div className="cardMeta"><strong>{card.name}</strong><span className="muted">#{card.localId}</span><span className="chip">{chosen?"✓ Ausgewählt":"+ Zum Shop hinzufügen"}</span></div>
 </button>})}</div>
 {entries.length>0&&<section className="sectionBlock"><h2>Ausgewählte Karten ({entries.length})</h2>{entries.map(([id,l])=><div key={id} className="accountCard" style={{display:"block",margin:"12px 0"}}>
 <strong>{l.card.name} · {l.card.localId} · {l.setName} ({l.language})</strong>
 <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(130px,1fr))",gap:12,marginTop:12}}>
 <label>Variante<select style={fieldStyle} value={l.variant} onChange={e=>change(id,{variant:e.target.value})}>{variants.map(x=><option key={x}>{x}</option>)}</select></label>
 <label>Zustand<select style={fieldStyle} value={l.condition} onChange={e=>change(id,{condition:e.target.value})}>{conditions.map(x=><option key={x}>{x}</option>)}</select></label>
 <label>Stückzahl<input style={fieldStyle} type="number" min="0" value={l.quantity} onChange={e=>change(id,{quantity:Number(e.target.value)})}/></label>
 <label>VK-Preis €<input style={fieldStyle} inputMode="decimal" value={l.price} onChange={e=>change(id,{price:e.target.value})} placeholder="2,50"/></label>
 <label>Eigenes Foto (HTTPS-URL, optional)<input style={fieldStyle} type="url" value={l.photoUrl} onChange={e=>change(id,{photoUrl:e.target.value})} placeholder="https://…"/></label>\n <label>Verkauf freigeben<select style={fieldStyle} value={l.enabled?"yes":"no"} onChange={e=>change(id,{enabled:e.target.value==="yes"})}><option value="no">Nein</option><option value="yes">Ja, nach Prüfung</option></select></label>
 </div><div style={{display:"flex",gap:10,marginTop:12,flexWrap:"wrap"}}><button type="button" className="ghostButton" onClick={()=>addCondition(id)}>+ Weiteren Zustand hinzufügen</button><button type="button" className="ghostButton" onClick={()=>setSelected(old=>Object.fromEntries(Object.entries(old).filter(([k])=>k!==id)))}>Eintrag entfernen</button></div><small className="muted">{l.photoUrl?"Eigenes Exemplarfoto":"Referenzbild – zeigt nicht den tatsächlichen Kartenzustand"}</small></div>)}
 <button type="button" className="primaryButton" onClick={download}>WooCommerce-CSV herunterladen</button></section>}
 <p className="muted" style={{marginTop:24}}>Import über WordPress → Produkte → Importieren. Prüfe Karte, Bild, Sprache, Variante und Bestandsführung vor Veröffentlichung. Offizielle/TCGdex-Bild-URLs lassen sich nur importieren, wenn WooCommerce die URL abrufen darf und die Bildrechte geklärt sind. Der Import synchronisiert noch keine vorhandenen Angebote und darf nicht blind mehrfach wiederholt werden.</p>
 </>}</AppShell>
}
