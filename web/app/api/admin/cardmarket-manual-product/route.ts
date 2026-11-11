import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
import {spawn} from 'node:child_process';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const SCRIPT='/home/tv/cardshop/scripts/cardmarket/admin/cardmarket-manual-product-review.py';
export async function POST(request:Request){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 const body=await request.json().catch(()=>null);
 if(!body||typeof body!=='object'||Array.isArray(body))return Response.json({error:'invalid_payload'},{status:400});
 const d=body as Record<string,unknown>;
 const action=d.action;
 if(action!=='preview'&&action!=='confirm')return Response.json({error:'invalid_action'},{status:400});
 const result=await new Promise<{status:number;json:unknown}>(resolve=>{
  const child=spawn('python3',[SCRIPT,'--action',action],{stdio:['pipe','pipe','pipe']});
  let output='';let done=false;
  const finish=(status:number,json:unknown)=>{if(done)return;done=true;clearTimeout(timer);resolve({status,json})};
  const timer=setTimeout(()=>{child.kill();finish(504,{error:'cardmarket_preview_timeout'})},52000);
  child.stdout.on('data',(b:Buffer)=>{output+=b.toString();if(output.length>100000)child.kill()});
  child.stderr.on('data',()=>{});
  child.on('error',()=>finish(503,{error:'manual_review_service_unavailable'}));
  child.on('close',code=>{let json:unknown;try{json=JSON.parse(output)}catch{json={error:'preview_service_failed'}}finish(code===0?200:code===2?422:503,json)});
  child.stdin.on('error',()=>{});
  child.stdin.end(JSON.stringify(d));
 });
 return Response.json(result.json,{status:result.status,headers:{'Cache-Control':'no-store'}});
}
