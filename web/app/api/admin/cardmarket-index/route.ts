import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const run=promisify(execFile);
const SCRIPT='/home/tv/cardshop/scripts/cardmarket/admin/cardmarket_index_monitor.py';
// Read-only status of the expansion-index scan; ?download=review-groups
// returns the grouped variant review list as CSV.
export async function GET(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const download=new URL(request.url).searchParams.get('download');
 try{
  if(download==='review-groups'){
   const {stdout}=await run('python3',[SCRIPT,'--review-groups-csv'],{timeout:15000,maxBuffer:16*1024*1024});
   const date=new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Berlin'});
   return new Response('﻿'+stdout,{headers:{'Content-Type':'text/csv; charset=utf-8','Content-Disposition':`attachment; filename="varianten-pruefgruppen-${date}.csv"`,'Cache-Control':'private, no-store'}});
  }
  if(download)return Response.json({error:'invalid_download'},{status:400});
  const {stdout}=await run('python3',[SCRIPT],{timeout:30000,maxBuffer:1024*1024});
  return Response.json(JSON.parse(stdout),{headers:{'Cache-Control':'no-store'}});
 }catch{return Response.json({error:'index_monitor_unavailable'},{status:503})}
}
