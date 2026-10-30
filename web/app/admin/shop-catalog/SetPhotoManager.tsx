"use client";
import {useEffect,useState} from "react";
type Photo={id:string;name:string;uploadedAt:string;size:number};
type Offer={id:number;title:string;set_id:string;language:string;variant:string;condition:string;card_id:string};
export function SetPhotoManager({setId,language,offers}:{setId:string;language:string;offers:Offer[]}){
 const [photos,setPhotos]=useState<Photo[]>([]),[error,setError]=useState(""),[selection,setSelection]=useState<Record<string,string>>({}),[busy,setBusy]=useState("");
 const link="https://cardyssey.de/admin/shop-photos?setId="+encodeURIComponent(setId)+"&language="+encodeURIComponent(language);
 const qr="https://api.qrserver.com/v1/create-qr-code/?size=210x210&data="+encodeURIComponent(link);
 const candidates=offers.filter(o=>o.set_id===setId&&o.language===language);
 const load=async()=>{try{const r=await fetch("/api/admin/shop/set-photos?setId="+encodeURIComponent(setId)+"&language="+encodeURIComponent(language),{cache:"no-store"});if(!r.ok)throw Error("Fotos konnten nicht geladen werden");setPhotos(await r.json());setError("")}catch(e){setError(String(e))}};
 useEffect(()=>{void load()},[setId,language]);
 async function assign(photoId:string){
  const offerId=Number(selection[photoId]);if(!offerId)return;
  setBusy(photoId);setError("");
  try{const r=await fetch("/api/admin/shop/assign-photo",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({photoId,offerId})});if(!r.ok)throw Error((await r.json()).error||"Zuordnung fehlgeschlagen");setSelection(old=>({...old,[photoId]:""}))}catch(e){setError(String(e))}finally{setBusy("")}
 }
 return <section className="accountCard" style={{margin:"22px 0",display:"block"}}>
  <h2>Handyfotos für dieses Set</h2>
  <div style={{display:"flex",flexWrap:"wrap",alignItems:"center",gap:20,marginBottom:18}}>
   <img src={qr} width={170} height={170} alt="QR-Code für den Set-Foto-Upload"/>
   <div><p>QR-Code am PC mit dem Handy scannen. Alle Bilder werden zunächst für <strong>{setId} ({language})</strong> gesammelt.</p>
    <a href={link} target="_blank" rel="noopener noreferrer">Uploadseite öffnen</a><p className="muted">Die QR-Grafik wird von einem externen QR-Dienst erzeugt; sie enthält nur den Link zur geschützten Uploadseite, keine Zugangsdaten.</p>
    <button type="button" className="ghostButton" onClick={()=>void load()}>Fotos aktualisieren</button>
   </div>
  </div>
  {error&&<p role="alert">{error}</p>}
  <p className="muted">{photos.length} Fotos hochgeladen · {candidates.length} gespeicherte Angebote in diesem Set</p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(175px,1fr))",gap:14}}>
   {photos.map(photo=><div key={photo.id} style={{border:"1px solid var(--border)",borderRadius:12,padding:10}}>
    <img src={"/api/shop/set-photo/"+language+"/"+setId+"/"+photo.id} alt={photo.name} style={{width:"100%",height:170,objectFit:"contain"}}/>
    <small style={{display:"block",overflowWrap:"anywhere"}}>{photo.name}</small>
    <select aria-label={"Karte für "+photo.name} style={{width:"100%",margin:"10px 0",minHeight:36}} value={selection[photo.id]||""} onChange={e=>setSelection(old=>({...old,[photo.id]:e.target.value}))}>
     <option value="">Angebot auswählen</option>
     {candidates.map(o=><option value={o.id} key={o.id}>{o.title} · {o.variant} · {o.condition}</option>)}
    </select>
    <button type="button" className="ghostButton" disabled={!selection[photo.id]||!!busy} onClick={()=>void assign(photo.id)}>Foto zuordnen</button>
   </div>)}
  </div>
  {!candidates.length&&<p className="muted">Lege zunächst mindestens ein Shopangebot für dieses Set als Entwurf an. Anschließend kannst du Bilder zuweisen.</p>}
 </section>
}
