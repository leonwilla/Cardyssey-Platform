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
 if(!body||typeof body!=='object'||Array.isArray(body)||(body as {action?:string}).action!=='resume')return Response.json({error:'invalid_action'},{status:400});
 try{
  await exec('/mnt/c/Windows/System32/schtasks.exe',['/Run','/TN','Cardyssey Cardmarket Manual Resume'],{timeout:10000,maxBuffer:14000});
  return Response.json({requested:true,message:'resume_task_triggered_session_gate_applies'},{headers:{'Cache-Control':'no-store'}});
 }catch{return Response.json({error:'resume_task_not_available'},{status:503})}
}
