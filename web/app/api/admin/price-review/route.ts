import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
import {spawn} from 'node:child_process';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function POST(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const data=await request.json().catch(()=>null);
 if(!data||typeof data.cardId!=='string'||!/^[a-zA-Z0-9_-]{2,90}$/.test(data.cardId)||
    !['AUTO','NO_VERIFIED_SALE','OFFER_REVIEW','VERIFIED'].includes(data.status)||
    ![7,14,30].includes(data.refreshDays)||typeof data.showOfferReferences!=='boolean'||
    typeof data.note!=='string'||data.note.length>500)
   return Response.json({error:'invalid_review'},{status:400});
 return new Promise<Response>(resolve=>{
  const proc=spawn('python3',['/home/tv/cardshop/scripts/ebay-collector/price_review_admin.py'],{stdio:['pipe','pipe','pipe']});
  let stdout='',stderr='';
  const timeout=setTimeout(()=>proc.kill(),12000);
  proc.stdout.on('data',(x:Buffer)=>{stdout+=x.toString().slice(0,10000)});
  proc.stderr.on('data',(x:Buffer)=>{stderr+=x.toString().slice(0,2000)});
  proc.on('error',()=>{clearTimeout(timeout);resolve(Response.json({error:'review_service_unavailable'},{status:503}))});
  proc.on('close',code=>{clearTimeout(timeout);let result:{error?:string}|null=null;try{result=JSON.parse(stdout)}catch{}
    resolve(Response.json(result??{error:'review_service_unavailable'},{status:code===0?200:code===2?400:503,headers:{'Cache-Control':'no-store'}}));});
  proc.stdin.end(JSON.stringify(data));
 });
}
