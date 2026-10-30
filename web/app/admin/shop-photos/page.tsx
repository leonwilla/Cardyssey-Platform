"use client";
import {useEffect,useState} from "react";
import {useSearchParams} from "next/navigation";
type Photo={id:string;name:string;uploadedAt:string;size:number;setId:string;language:string};
export default function SetPhotosPage(){
 const params=useSearchParams();
 const setId=params.get("setId")||"",language=params.get("language")||"de";
 const [photos,setPhotos]=useState<Photo[]>([]),[error,setError]=useState(""),[busy,setBusy]=useState(false),[done,setDone]=useState(0);
 const valid=/^[a-z0-9_-]{1,100}$/i.test(setId);
 const load=async()=>{if(!valid)return;try{const r=await fetch("/api/admin/shop/set-photos?setId="+encodeURIComponent(setId)+"&language="+encodeURIComponent(language),{cache:"no-store"});if(!r.ok)throw Error(r.status===403?"Bitte als Shop-Admin anmelden.":"Fotos konnten nicht geladen werden");setPhotos(await r.json())}catch(e){setError(String(e))}};
 useEffect(()=>{void load()},[setId,language]);
 async function upload(files:FileList|null){
  if(!files?.length||busy)return;setBusy(true);setError("");setDone(0);
  let count=0;
  try{for(const file of Array.from(files)){const body=new FormData();body.set("setId",setId);body.set("language",language);body.set("photo",file);
   const response=await fetch("/api/admin/shop/set-photos",{method:"POST",body});
   if(!response.ok){const data=await response.json().catch(()=>({error:"upload_failed"}));throw Error(file.name+": "+data.error)}
   count++;setDone(count);
  }await load()}catch(e){setError(e instanceof Error?e.message:String(e))}finally{setBusy(false)}
 }
 return <main style={{maxWidth:740,margin:"auto",padding:24,color:"#1d2924",background:"#f4eee4",minHeight:"100vh",fontFamily:"Arial,sans-serif"}}>
  <a href="/admin/shop-catalog">← Shopverwaltung</a>
  <h1>Set-Fotos hochladen</h1>
  <p><strong>{setId||"Kein Set ausgewählt"}</strong> · {language.toUpperCase()}</p>
  <p>Fotografiere Vorder- und Rückseiten sowie Details. Alle Bilder bleiben zunächst diesem Set zugeordnet und können später am PC einzelnen Angeboten zugewiesen werden.</p>
  {!valid?<p role="alert">Bitte ein Set über die Shopverwaltung auswählen.</p>:<>
  <label style={{display:"block",padding:25,border:"2px dashed #bdb3a4",borderRadius:16,background:"#fbf7f0",margin:"22px 0"}}>
   <strong>{busy?"Fotos werden übertragen …":"Fotos auswählen oder Kamera öffnen"}</strong>
   <input type="file" multiple accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={e=>void upload(e.target.files)} style={{display:"block",marginTop:15,maxWidth:"100%"}}/>
  </label>
  <p role="status">{busy?done+" Fotos hochgeladen":photos.length+" Fotos für dieses Set gespeichert"}</p>
  {error&&<p role="alert" style={{color:"#ad3421"}}>{error}</p>}
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(135px,1fr))",gap:12}}>
   {photos.map(photo=><figure key={photo.id} style={{margin:0,background:"#fff",padding:8,borderRadius:12}}>
    <img style={{width:"100%",height:150,objectFit:"contain"}} src={"/api/shop/set-photo/"+language+"/"+setId+"/"+photo.id} alt={photo.name}/>
    <figcaption style={{fontSize:11,overflowWrap:"anywhere"}}>{photo.name}</figcaption>
   </figure>)}
  </div>
  </>}
 </main>
}
