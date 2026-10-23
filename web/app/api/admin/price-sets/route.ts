import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { authenticatedBackendFetch, readBackendJson } from '@/lib/server/cardyssey-api';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const exec=promisify(execFile);
export async function GET(){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 try{
  const {stdout}=await exec('python3',['/home/tv/cardshop/scripts/price_monitor_ebay.py'],{timeout:15000,maxBuffer:4000000});
  return Response.json(JSON.parse(stdout),{headers:{'Cache-Control':'no-store'}});
 }catch{return Response.json({error:'live_monitor_unavailable'},{status:503});}
}
