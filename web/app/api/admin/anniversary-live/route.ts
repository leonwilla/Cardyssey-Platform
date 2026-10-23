import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { authenticatedBackendFetch, readBackendJson } from "@/lib/server/cardyssey-api";
export const dynamic="force-dynamic";
export const runtime="nodejs";
const exec=promisify(execFile);
export async function GET(){
 const response=await authenticatedBackendFetch("/api/v1/me");
 if(!response.ok)return Response.json({error:"unauthorized"},{status:401});
 const user=await readBackendJson(response) as {id?:string;role?:string}|null;
 const allow=(process.env.CARDYSSEY_PRIVATE_USER_IDS??"").split(",");
 if(!user?.id||!allow.includes(user.id))return Response.json({error:"forbidden"},{status:403});
 try {
  const query="SELECT card_id FROM ebay_price_cache WHERE language_code='de' AND source='CARDYSSEY_EBAY' AND ((card_id LIKE '30th-%') OR (card_id LIKE 'mep-%')) AND base_eur > 0";
  const {stdout}=await exec("docker",["exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-Atc",query],{timeout:8000,maxBuffer:100000});
  return Response.json({pricedIds:stdout.split(/\r?\n/).filter(Boolean),checkedAt:new Date().toISOString()},{headers:{"Cache-Control":"no-store"}});
 }catch{return Response.json({error:"price_check_unavailable"},{status:503});}
}
