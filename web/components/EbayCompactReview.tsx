'use client';
import {useEffect,useState} from 'react';

type Review={status:string;refreshDays:number;showOfferReferences:boolean;note:string};
export type ReviewDecision='AUTO'|'VERIFIED'|'NO_VERIFIED_SALE';
export function EbayCompactReview({cardId,review,onSaved}:{cardId:string;review?:Review;onSaved:(value:{status:ReviewDecision;refreshDays:number;updatedAt:string})=>void}){
 const [status,setStatus]=useState<ReviewDecision>(review?.status==='VERIFIED'?'VERIFIED':review?.status==='NO_VERIFIED_SALE'?'NO_VERIFIED_SALE':'AUTO');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 useEffect(()=>{setStatus(review?.status==='VERIFIED'?'VERIFIED':review?.status==='NO_VERIFIED_SALE'?'NO_VERIFIED_SALE':'AUTO');setError('')},[cardId,review?.status]);
 async function save(){setBusy(true);setError('');try{
  const refreshDays=status==='NO_VERIFIED_SALE'?30:7;
  const r=await fetch('/api/admin/price-review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cardId,status,refreshDays,showOfferReferences:true,note:review?.note||''})});
  if(!r.ok)throw Error('Prüfstatus konnte nicht gespeichert werden.');
  onSaved({status,refreshDays,updatedAt:new Date().toISOString()});
 }catch(err){setError(err instanceof Error?err.message:'Speichern fehlgeschlagen')}finally{setBusy(false)}}
 return <div style={{display:'flex',gap:10,alignItems:'end',flexWrap:'wrap',marginTop:12,padding:12,border:'1px solid var(--border)',borderRadius:12}}>
  <label style={{flex:'1 1 190px',display:'grid',gap:5,fontSize:13}}><strong>Prüfstatus</strong>
   <select value={status} onChange={e=>setStatus(e.target.value as ReviewDecision)}>
    <option value="AUTO">Offen · weiter prüfen</option>
    <option value="VERIFIED">Fertig · alles korrekt (7 Tage)</option>
    <option value="NO_VERIFIED_SALE">Keine Verkäufe (30 Tage)</option>
   </select>
  </label>
  <button className="primaryButton" type="button" disabled={busy} onClick={()=>void save()}>{busy?'Speichere …':'Speichern'}</button>
  {error&&<small role="alert">{error}</small>}
 </div>;
}
