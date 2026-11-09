import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const exec=promisify(execFile);
export async function GET(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const p=new URL(request.url).searchParams;
 const language=p.get('language')||'de',scope=p.get('scope')||'current';
 const page=Number(p.get('page')||'0'),search=(p.get('search')||'').slice(0,120);
 if(!['de','en'].includes(language)||!['all','current'].includes(scope)||!Number.isInteger(page)||page<0||page>2000)return Response.json({error:'invalid_query'},{status:400});
 try{
  const {stdout}=await exec('python3',['/home/tv/cardshop/scripts/cardmarket-live-failures.py','--language',language,'--scope',scope,'--page',String(page),'--search',search],{timeout:20000,maxBuffer:200000});
  return Response.json(JSON.parse(stdout),{headers:{'Cache-Control':'no-store'}});
 }catch{return Response.json({error:'scan_failure_list_unavailable'},{status:503})}
}
