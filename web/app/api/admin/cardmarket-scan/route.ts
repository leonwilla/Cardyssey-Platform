import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const run=promisify(execFile);
export async function GET(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const language=new URL(request.url).searchParams.get('language')||'de';
 if(!['de','en'].includes(language))return Response.json({error:'invalid_language'},{status:400});
 try{
  const {stdout}=await run('python3',['/home/tv/cardshop/scripts/cardmarket_scan_monitor.py','--language',language],{timeout:15000,maxBuffer:160000});
  return Response.json(JSON.parse(stdout),{headers:{'Cache-Control':'no-store'}});
 }catch{return Response.json({error:'scan_monitor_unavailable'},{status:503})}
}
