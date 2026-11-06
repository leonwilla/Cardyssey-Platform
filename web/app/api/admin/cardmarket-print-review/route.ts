import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
import {spawn} from 'node:child_process';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const SCRIPT='/home/tv/cardshop/scripts/cardmarket-print-review-admin.py';
function run(action:'list'|'review',payload:Record<string,unknown>):Promise<{status:number;data:unknown}>{
 return new Promise(resolve=>{
  const child=spawn('python3',[SCRIPT,'--action',action],{stdio:['pipe','pipe','pipe']});
  let stdout='';
  const timeout=setTimeout(()=>child.kill(),20000);
  child.stdout.on('data',(b:Buffer)=>{stdout+=b.toString();if(stdout.length>250000)child.kill()});
  child.stderr.on('data',()=>{});
  child.on('error',()=>{clearTimeout(timeout);resolve({status:503,data:{error:'review_service_unavailable'}})});
  child.on('close',code=>{
    clearTimeout(timeout);
    let data:unknown;
    try{data=JSON.parse(stdout)}catch{data={error:'review_service_failed'}}
    resolve({status:code===0?200:code===2?400:503,data});
  });
  child.stdin.on('error',()=>{});
  child.stdin.end(JSON.stringify(payload));
 });
}
export async function GET(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const p=new URL(request.url).searchParams;
 const result=await run('list',{language:p.get('language')||'de',status:p.get('status')||'PENDING_REVIEW',
  page:p.get('page')||'0',search:p.get('search')||''});
 return Response.json(result.data,{status:result.status,headers:{'Cache-Control':'no-store'}});
}
export async function POST(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const data=await request.json().catch(()=>null);
 if(!data||typeof data!=='object'||Array.isArray(data))return Response.json({error:'invalid_payload'},{status:400});
 const result=await run('review',data);
 return Response.json(result.data,{status:result.status,headers:{'Cache-Control':'no-store'}});
}
