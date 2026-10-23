import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {priceMonitorAllowed} from '@/lib/server/price-monitor-access';
export const dynamic='force-dynamic';export const runtime='nodejs';
const exec=promisify(execFile);
export async function GET(){if(!await priceMonitorAllowed())return Response.json({error:'forbidden'},{status:403});try{const {stdout}=await exec('python3',['/home/tv/cardshop/scripts/price_jobs_overview.py'],{timeout:10000,maxBuffer:200000});return Response.json(JSON.parse(stdout),{headers:{'Cache-Control':'no-store'}})}catch{return Response.json({error:'monitor_unavailable'},{status:503})}}
