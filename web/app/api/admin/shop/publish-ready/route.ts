import {isShopAdmin} from "@/lib/server/shop-photos";
import {shopSql} from "@/lib/server/native-shop-db";
export const runtime="nodejs";export const dynamic="force-dynamic";
export async function POST(request:Request){
 if(!await isShopAdmin())return Response.json({error:"forbidden"},{status:403});
 const origin=request.headers.get("origin");
 if(!origin||![new URL(request.url).origin,process.env.CARDYSSEY_PUBLIC_ORIGIN||"https://cardyssey.de"].includes(origin))return Response.json({error:"origin_mismatch"},{status:403});
 let ids:number[];
 try{const b=await request.json();ids=b.ids}catch{return Response.json({error:"invalid_json"},{status:400})}
 if(!Array.isArray(ids)||ids.length<1||ids.length>500||!ids.every(v=>Number.isSafeInteger(v)&&v>0)||new Set(ids).size!==ids.length)return Response.json({error:"invalid_ids"},{status:400});
 try{
  const list=ids.join(",");
  // Only complete drafts can be published; all-or-none guarded by a single statement.
  const count=Number(await shopSql(`WITH eligible AS (SELECT COUNT(*) AS n FROM cardyssey_shop.offers WHERE id IN (${list}) AND status='draft' AND price_minor>0 AND stock_quantity>reserved_quantity), changed AS (
   UPDATE cardyssey_shop.offers SET status='published',version=version+1,updated_at=now()
   WHERE id IN (${list}) AND status='draft' AND price_minor>0 AND stock_quantity>reserved_quantity AND (SELECT n FROM eligible)=${ids.length}
   RETURNING id
  ) SELECT COUNT(*) FROM changed`));
  if(count!==ids.length)return Response.json({error:"not_all_ready"},{status:409});
  return Response.json({ok:true,published:count});
 }catch{return Response.json({error:"bulk_publish_failed"},{status:503})}
}
