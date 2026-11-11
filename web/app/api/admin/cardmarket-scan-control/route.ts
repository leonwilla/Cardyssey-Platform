import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const exec=promisify(execFile);
// Use the task registered in the interactive Windows user's session; don't
// launch Edge or access any browser passwords from the web-server account.
export async function POST(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const body=await request.json().catch(()=>null);
 if(!body||typeof body!=='object'||Array.isArray(body)||!['resume','rescan','retry'].includes(String((body as {action?:string}).action)))return Response.json({error:'invalid_action'},{status:400});
 try{
  const action=String((body as {action?:string}).action);
  let reset:null|{ok:boolean;startedAt:string;historyPreserved:boolean}=null;
  if(action==='rescan'){
   const {stdout}=await exec('python3',['/home/tv/cardshop/scripts/cardmarket/admin/cardmarket-reset-rescan.py','--execute'],{timeout:35000,maxBuffer:14000});
   reset=JSON.parse(stdout);
  }
  let retry:null|{ok:boolean;cardId:string;variantId:string}=null;
  if(action==='retry'){
   const d=body as Record<string,unknown>;
   if(!['de','en'].includes(String(d.language))||typeof d.cardId!=='string'||typeof d.variantId!=='string')return Response.json({error:'invalid_card_identity'},{status:400});
   const {stdout}=await exec('python3',['/home/tv/cardshop/scripts/cardmarket/admin/cardmarket-retry-one.py','--language',String(d.language),'--card',d.cardId,'--variant',d.variantId],{timeout:15000,maxBuffer:14000});
   retry=JSON.parse(stdout);
  }
  await exec('/mnt/c/Windows/System32/schtasks.exe',['/Run','/TN','Cardyssey Cardmarket Manual Resume'],{timeout:10000,maxBuffer:14000});
  return Response.json({requested:true,rescan:reset,retry,message:'resume_task_triggered_session_gate_applies'},{headers:{'Cache-Control':'no-store'}});
 }catch(e){const message=String(e);return Response.json({error:message.includes('card_variant_not_in_current_queue')?'card_variant_not_in_current_queue':message.includes('stop_failed')?'scan_stop_failed':'scan_control_failed'},{status:503})}
}
