import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
import {execFile} from 'node:child_process';import {promisify} from 'node:util';import {authenticatedBackendFetch,readBackendJson} from '@/lib/server/cardyssey-api';
export const runtime='nodejs';export const dynamic='force-dynamic';const exec=promisify(execFile);
async function handle(req:Request,action:'start'|'status'){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const p=action==='start'?await req.json().catch(()=>({})):Object.fromEntries(new URL(req.url).searchParams);
 if(typeof p.cardId!=='string'||!/^[a-zA-Z0-9_-]{2,90}$/.test(p.cardId))return Response.json({error:'invalid_card'},{status:400});
 if(action==='start'&&(typeof p.query!=='string'||p.query.length<3||p.query.length>160))return Response.json({error:'invalid_query'},{status:400});
 try{const {stdout}=await exec('python3',['/home/tv/cardshop/scripts/price_card_test.py',action,p.cardId,...(action==='start'?[p.query]:[])],{timeout:15000,maxBuffer:100000});const v=JSON.parse(stdout);return Response.json(v,{status:v.error?409:200,headers:{'Cache-Control':'no-store'}})}catch{return Response.json({error:'test_unavailable'},{status:503})}
}
export async function POST(r:Request){return handle(r,'start')}export async function GET(r:Request){return handle(r,'status')}
