import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
export const dynamic='force-dynamic';
export const runtime='nodejs';
const exec=promisify(execFile);
export async function GET(){
 if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});
 try{
  const {stdout}=await exec('python3',['/home/tv/cardshop/scripts/price_source_coverage.py'],{timeout:15000,maxBuffer:250000});
  return Response.json(JSON.parse(stdout),{headers:{'Cache-Control':'private, no-store'}});
 }catch{return Response.json({error:'coverage_unavailable'},{status:503});}
}
