"use client";
import {useEffect,useState} from "react";
type Photo={id:string;name:string;uploadedAt:string;size:number};
type Offer={id:number;title:string;set_id:string;language:string;variant:string;condition:string;card_id:string};
export function SetPhotoManager({setId,language,offers,onEditOffer}:{setId:string;language:string;offers:Offer[];onEditOffer?:(id:number)=>void}){
 const [photos,setPhotos]=useState<Photo[]>([]),[success,setSuccess]=useState(""),[error,setError]=useState(""),[selection,setSelection]=useState<Record<string,string>>({}),[roles,setRoles]=useState<Record<string,string>>({}),[busy,setBusy]=useState("");
 const link="https://cardyssey.de/admin/shop-photos?setId="+encodeURIComponent(setId)+"&language="+encodeURIComponent(language);
 const qr="https://api.qrserver.com/v1/create-qr-code/?size=210x210&data="+encodeURIComponent(link);
 const candidates=offers.filter(o=>o.set_id===setId&&o.language===language);
 const load=async()=>{try{const r=await fetch("/api/admin/shop/set-photos?setId="+encodeURIComponent(setId)+"&language="+encodeURIComponent(language),{cache:"no-store"});if(!r.ok)throw Error("Fotos konnten nicht geladen werden");setPhotos(await r.json());setError("")}catch(e){setError(String(e))}};
 useEffect(()=>{void load()},[setId,language]);
 async function removePhoto(photoId:string){if(busy)return;if(!confirm("Foto dauerhaft entfernen? Falls es einem Angebot zugeordnet ist, wird die Zuordnung ebenfalls entfernt."))return;setBusy(photoId);setError("");try{const r=await fetch("/api/admin/shop/photo-delete",{method:"DELETE",headers:{"Content-Type":"application/json"},body:JSON.stringify({language,setId,id:photoId,detach:true})});if(!r.ok)throw Error((await r.json()).error||"Foto konnte nicht gelöscht werden");await load();setSuccess("Foto entfernt.")}catch(e){setError(String(e))}finally{setBusy("")}}
 async function assign(photoId:string){
  const offerId=Number(selection[photoId]);if(!offerId)return;
  setBusy(photoId);setError("");setSuccess("");
  try{const r=await fetch("/api/admin/shop/assign-photo",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({photoId,offerId,role:roles[photoId]||"front"})});if(!r.ok)throw Error((await r.json()).error||"Zuordnung fehlgeschlagen");setSuccess("Foto wurde dem Angebot zugeordnet. Es erscheint nach der Aktualisierung im Shop, sobald das Angebot veröffentlicht ist.");setSelection(old=>({...old,[photoId]:""}))}catch(e){setError(String(e))}finally{setBusy("")}
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
  {error&&<p role="alert">{error}</p>}{success&&<p role="status" style={{border:"1px solid #53705d",borderRadius:8,padding:10}}>{success}</p>}
  <p className="muted">{photos.length} Fotos hochgeladen · {candidates.length} gespeicherte Angebote in diesem Set. Wichtig: Ein Foto muss einem Angebot zugeordnet werden, bevor es im Shop erscheint.</p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(175px,1fr))",gap:14}}>
   {photos.map(photo=><div key={photo.id} style={{border:"1px solid var(--border)",borderRadius:12,padding:10}}>
    <img src={"/api/shop/set-photo/"+language+"/"+setId+"/"+photo.id} alt={photo.name} style={{width:"100%",height:170,objectFit:"contain"}}/>
    <small style={{display:"block",overflowWrap:"anywhere"}}>{photo.name}</small>
    <select aria-label={"Karte für "+photo.name} style={{width:"100%",margin:"10px 0",minHeight:36}} value={selection[photo.id]||""} onChange={e=>setSelection(old=>({...old,[photo.id]:e.target.value}))}>
     <option value="">Angebot auswählen</option>
     {candidates.map(o=><option value={o.id} key={o.id}>{o.title} · {o.variant} · {o.condition}</option>)}
    </select>
    <select aria-label={"Bildtyp für "+photo.name} style={{width:"100%",marginBottom:10,minHeight:36}} value={roles[photo.id]||"front"} onChange={e=>setRoles(old=>({...old,[photo.id]:e.target.value}))}><option value="front">Vorderseite</option><option value="back">Rückseite</option><option value="detail">Detailfoto</option></select>
    <button type="button" className="ghostButton" disabled={!selection[photo.id]||!!busy} onClick={()=>void assign(photo.id)}>Foto zuordnen</button><button type="button" className="ghostButton" disabled={!!busy} onClick={()=>void removePhoto(photo.id)}>Foto löschen</button>{selection[photo.id]&&<button type="button" className="ghostButton" style={{marginTop:8}} onClick={()=>onEditOffer?.(Number(selection[photo.id]))}>Angebot bearbeiten →</button>}
   </div>)}
  </div>
  {!candidates.length&&<p className="muted">Lege zunächst mindestens ein Shopangebot für dieses Set als Entwurf an. Anschließend kannst du Bilder zuweisen.</p>}
 </section>
}
