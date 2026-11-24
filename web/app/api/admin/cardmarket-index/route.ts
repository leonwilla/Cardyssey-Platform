import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const run=promisify(execFile);
const SCRIPT='/home/tv/cardshop/scripts/cardmarket/admin/cardmarket_index_monitor.py';
const DOWNLOADS:Record<string,{flag:string;name:string}>={
 'review-groups':{flag:'--review-groups-csv',name:'varianten-pruefgruppen'},
 'guide-changes':{flag:'--guide-changes-csv',name:'cardmarket-preisaenderungen'},
};
// Read-only status of the expansion-index scan; ?download=review-groups or
// ?download=guide-changes returns the CSV list.
export async function GET(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const download=new URL(request.url).searchParams.get('download');
 try{
  if(download){
   const target=DOWNLOADS[download];
   if(!target)return Response.json({error:'invalid_download'},{status:400});
   const {stdout}=await run('python3',[SCRIPT,target.flag],{timeout:20000,maxBuffer:32*1024*1024});
   const date=new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Berlin'});
   return new Response('﻿'+stdout,{headers:{'Content-Type':'text/csv; charset=utf-8','Content-Disposition':`attachment; filename="${target.name}-${date}.csv"`,'Cache-Control':'private, no-store'}});
  }
  const {stdout}=await run('python3',[SCRIPT],{timeout:30000,maxBuffer:1024*1024});
  return Response.json(JSON.parse(stdout),{headers:{'Cache-Control':'no-store'}});
 }catch{return Response.json({error:'index_monitor_unavailable'},{status:503})}
}
