import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
export const runtime='nodejs';export const dynamic='force-dynamic';
const exec=promisify(execFile);
export async function GET(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const language=new URL(request.url).searchParams.get('language');
 if(!['de','en','ja','ko','zh-cn','zh-tw'].includes(language??''))return Response.json({error:'invalid_language'},{status:400});
 try{const {stdout}=await exec('python3',['/home/tv/cardshop/scripts/price_monitor_tcg_counts.py',language!],{timeout:25000,maxBuffer:200000});return Response.json(JSON.parse(stdout),{headers:{'Cache-Control':'no-store'}})}catch{return Response.json({error:'counts_unavailable'},{status:503})}
}
