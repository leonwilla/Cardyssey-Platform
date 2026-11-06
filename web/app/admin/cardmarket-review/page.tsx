'use client';
import {useCallback,useEffect,useState} from 'react';
import {useRouter} from 'next/navigation';
import {AppShell} from '@/components/AppShell';
import type {User} from '@/lib/types';

import {CardReview,type Entry} from '@/components/CardmarketReviewCard';
type Result={total:number;items:Entry[];guide_date?:string};
const initial:Result={total:0,items:[]};
export default function CardmarketReviewPage(){
 const router=useRouter();
 const [user,setUser]=useState<User|null>(null);
 const [language,setLanguage]=useState('de');
 const [status,setStatus]=useState('PENDING_REVIEW');
 const [search,setSearch]=useState('');
 const [page,setPage]=useState(0);
 const [result,setResult]=useState<Result>(initial);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 const reload=useCallback(async()=>{
  if(!user)return;
  setLoading(true);setError('');
  try{
   const params=new URLSearchParams({language,status,search,page:String(page)});
   const r=await fetch('/api/admin/cardmarket-print-review?'+params,{cache:'no-store'});
   if(!r.ok)throw Error('Prüfliste konnte nicht geladen werden');
   setResult(await r.json());
  }catch(e){setError(e instanceof Error?e.message:'Fehler')}
  finally{setLoading(false)}
 },[user,language,status,search,page]);
 useEffect(()=>{const term=new URLSearchParams(window.location.search).get('search');if(term)setSearch(term.slice(0,90))},[]);
 useEffect(()=>{fetch('/api/auth/me',{cache:'no-store'}).then(async r=>{
  if(!r.ok){router.replace('/login');return}
  const data=await r.json() as User;
  if(!data.canAdmin&&data.role!=='ADMIN'&&data.role!=='FOUNDER'){router.replace('/account');return}
  setUser(data);
 }).catch(()=>router.replace('/login'))},[router]);
 useEffect(()=>{void reload()},[reload]);
 return <AppShell active="/admin/prices" user={user}>
  <section className="pageIntro"><div>
   <span className="eyebrowText">Admin · Cardmarket</span>
   <h1>Druckvarianten zuordnen</h1>
   <p>Offizielle Produktkandidaten aus dem Cardmarket-Katalog prüfen. Der öffentliche Preisguide liefert keinen garantiert sprach- und zustandsspezifischen NM-Wert.</p>
  </div></section>
  <div className="filterRow" style={{gap:10,marginBottom:18}}>
   <button className="ghostButton" onClick={()=>router.push('/admin/prices')}>← Preisübersicht</button>
   <select aria-label="Sprache" value={language} onChange={e=>{setLanguage(e.target.value);setPage(0)}}>
    <option value="de">Deutsch</option><option value="en">Englisch</option>
   </select>
   <select aria-label="Prüfstatus" value={status} onChange={e=>{setStatus(e.target.value);setPage(0)}}>
    <option value="PENDING_REVIEW">Offen</option><option value="CONFIRMED_PRINT">Bestätigt</option>
    <option value="DEFERRED">Zurückgestellt</option><option value="NO_MATCH">Kein Treffer</option>
    <option value="ALL">Alle</option>
   </select>
   <input aria-label="Karte suchen" placeholder="Karte, Nummer oder Set suchen" value={search}
    onChange={e=>{setSearch(e.target.value);setPage(0)}}/>
   <button className="ghostButton" onClick={()=>void reload()}>Aktualisieren</button>
  </div>
  <p>{loading?'Wird geladen …':result.total.toLocaleString('de-DE')+' Prüffälle'} · Seite {page+1}
  {result.guide_date&&<small> · Preisguide: {result.guide_date}</small>}</p>
  {error&&<p role="alert">{error}</p>}
  <div style={{display:'grid',gap:12}}>
   {result.items.map(item=><CardReview key={item.language+item.card_id+item.variant_id} entry={item} onSaved={()=>void reload()}/>)}
  </div>
  <div className="filterRow" style={{gap:10,marginTop:18}}>
   <button className="ghostButton" disabled={page===0} onClick={()=>setPage(p=>Math.max(0,p-1))}>← Zurück</button>
   <button className="ghostButton" disabled={(page+1)*50>=result.total} onClick={()=>setPage(p=>p+1)}>Weitere 50 →</button>
  </div>
 </AppShell>;
}
