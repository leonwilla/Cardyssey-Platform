import {isShopAdmin} from "@/lib/server/shop-photos";
import {shopSql,sqlLiteral} from "@/lib/server/native-shop-db";
export const runtime="nodejs";
export const dynamic="force-dynamic";

export async function POST(request:Request){
 if(!await isShopAdmin())return Response.json({error:"forbidden"},{status:403});
 const origin=request.headers.get("origin");
 const allowed=new Set([new URL(request.url).origin,process.env.CARDYSSEY_PUBLIC_ORIGIN||"https://cardyssey.de"]);
 if(!origin||!allowed.has(origin))return Response.json({error:"origin_mismatch"},{status:403});
 let id:number;
 try{id=Number((await request.json()).offerId)}catch{return Response.json({error:"invalid_json"},{status:400})}
 if(!Number.isSafeInteger(id)||id<1)return Response.json({error:"invalid_offer"},{status:400});
 try{
  const row=await shopSql(`WITH archived AS (
   UPDATE cardyssey_shop.offers SET status='archived',version=version+1,updated_at=now()
   WHERE id=${id} AND status IN ('published','draft') AND reserved_quantity=0
   RETURNING id,sku,stock_quantity,price_minor
  ), audit AS (
   INSERT INTO cardyssey_shop.audit_events(action,entity_type,entity_id,details)
   SELECT 'manual_sold','offer',id::text,jsonb_build_object('sku',sku,'quantity_at_sale',stock_quantity,'asking_price_minor',price_minor)
   FROM archived RETURNING id
  )
  SELECT COALESCE((SELECT id::text FROM archived),'')`);
  if(!row)return Response.json({error:"not_found_or_reserved"},{status:409});
  return Response.json({ok:true,id:Number(row)});
 }catch{return Response.json({error:"archive_failed"},{status:503})}
}
