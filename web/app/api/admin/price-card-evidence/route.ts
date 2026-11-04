import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const execute=promisify(execFile);
export async function GET(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const cardId=new URL(request.url).searchParams.get('cardId')??'';
 if(!/^[a-z0-9_-]{2,80}$/.test(cardId))return Response.json({error:'invalid_card_id'},{status:400});
 try{
  const {stdout}=await execute('python3',['/home/tv/cardshop/scripts/price_monitor_ebay_detail.py',cardId],{timeout:20000,maxBuffer:3000000});
  return Response.json(JSON.parse(stdout),{headers:{'Cache-Control':'private, no-store'}});
 }catch{return Response.json({error:'evidence_unavailable'},{status:503});}
}
