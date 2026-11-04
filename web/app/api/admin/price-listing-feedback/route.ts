import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
import {spawn} from 'node:child_process';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const decisions=['WRONG_CARD','VALID_SINGLE_SALE','MULTI_SELECTION','WRONG_VARIANT','PAID_PRICE_UNKNOWN','OTHER'];
export async function POST(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const body=await request.json().catch(()=>null);
 if(!body||typeof body.cardId!=='string'||!/^[a-zA-Z0-9_-]{2,90}$/.test(body.cardId)||
  typeof body.itemId!=='string'||!/^[0-9]{9,15}$/.test(body.itemId)||
  !decisions.includes(body.decision)||typeof body.note!=='string'||body.note.length>1000||
  typeof body.title!=='string'||body.title.length>500)return Response.json({error:'invalid_feedback'},{status:400});
 return await new Promise<Response>(resolve=>{
  const proc=spawn('python3',['/home/tv/cardshop/scripts/ebay-collector/learning_feedback.py'],{stdio:['pipe','pipe','pipe']});
  let result='';let complete=false;
  const timeout=setTimeout(()=>{proc.kill();if(!complete){complete=true;resolve(Response.json({error:'save_timeout'},{status:503}))}},13000);
  proc.stdout.on('data',(part:Buffer)=>{result+=part.toString().slice(0,15000)});
  proc.on('error',()=>{clearTimeout(timeout);if(!complete){complete=true;resolve(Response.json({error:'save_unavailable'},{status:503}))}});
  proc.on('close',code=>{clearTimeout(timeout);if(complete)return;complete=true;
   try{resolve(Response.json(JSON.parse(result),{status:code===0?200:code===2?400:503,headers:{'Cache-Control':'private, no-store'}}))}
   catch{resolve(Response.json({error:'save_unavailable'},{status:503}))}
  });
  proc.stdin.end(JSON.stringify(body));
 });
}
