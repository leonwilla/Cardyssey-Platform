import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {authenticatedBackendFetch,readBackendJson} from '@/lib/server/cardyssey-api';
export const runtime='nodejs';export const dynamic='force-dynamic';
const exec=promisify(execFile);
async function authorized(){const r=await authenticatedBackendFetch('/api/v1/me');if(!r.ok)return false;const u=await readBackendJson(r) as {id?:string;role?:string;canAdmin?:boolean}|null;return Boolean(u?.id&&(process.env.CARDYSSEY_PRIVATE_USER_IDS??'').split(',').includes(u.id)&&(u.role==='ADMIN'||u.role==='FOUNDER'||u.canAdmin));}
async function handle(request:Request,action:'start'|'status'){
 if(!await authorized())return Response.json({error:'forbidden'},{status:403});
 const setId=action==='start'?(await request.json().catch(()=>({}))).setId:new URL(request.url).searchParams.get('setId');
 if(!['30th','30th-c','mep'].includes(setId))return Response.json({error:'unsupported_set'},{status:400});
 try{const {stdout}=await exec('python3',['/home/tv/cardshop/scripts/price_set_jobs.py',action,setId],{timeout:15000,maxBuffer:100000});const data=JSON.parse(stdout);return Response.json(data,{status:data.error?409:200,headers:{'Cache-Control':'no-store'}});}catch{return Response.json({error:'job_unavailable'},{status:503});}
}
export async function GET(request:Request){return handle(request,'status')}
export async function POST(request:Request){return handle(request,'start')}
