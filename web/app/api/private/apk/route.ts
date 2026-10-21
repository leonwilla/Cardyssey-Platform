import { readFile } from "node:fs/promises";
import path from "node:path";
import { authenticatedBackendFetch, readBackendJson } from "@/lib/server/cardyssey-api";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export async function GET(){
 const me=await authenticatedBackendFetch("/api/v1/me");
 if(!me.ok)return new Response("Unauthorized",{status:401});
 const user=await readBackendJson(me) as {id?:string}|null;
 const allow=(process.env.CARDYSSEY_PRIVATE_USER_IDS??"").split(",").map(x=>x.trim());
 if(!user?.id||!allow.includes(user.id))return new Response("Forbidden",{status:403});
 const apk=await readFile(path.join(process.cwd(),"private-downloads","cardyssey-latest.apk"));
 return new Response(apk,{headers:{"Content-Type":"application/vnd.android.package-archive","Content-Disposition":"attachment; filename=cardyssey-latest.apk","Cache-Control":"private, no-store"}});
}
