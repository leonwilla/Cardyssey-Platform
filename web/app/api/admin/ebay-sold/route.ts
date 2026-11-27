import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const run=promisify(execFile);
const SCRIPT='/home/tv/cardshop/scripts/ebay/ebay_sold_monitor.py';
// Read-only status of the eBay sold scanner (Windows collector + import).
export async function GET(){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 try{
  const {stdout}=await run('python3',[SCRIPT],{timeout:30000,maxBuffer:1024*1024});
  return Response.json(JSON.parse(stdout),{headers:{'Cache-Control':'no-store'}});
 }catch{return Response.json({error:'ebay_sold_monitor_unavailable'},{status:503})}
}
