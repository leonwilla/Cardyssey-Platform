import {isShopAdmin} from "@/lib/server/shop-photos";
import {shopSql} from "@/lib/server/native-shop-db";
export const runtime="nodejs";export const dynamic="force-dynamic";
export async function GET(){
 if(!await isShopAdmin())return Response.json({error:"forbidden"},{status:403});
 try{
  const raw=await shopSql(`SELECT COALESCE(json_agg(row_to_json(t)),'[]'::json) FROM (
   SELECT a.id,a.created_at,a.entity_id AS offer_id,a.details->>'sku' AS sku,a.details->>'quantity_at_sale' AS quantity,a.details->>'asking_price_minor' AS asking_price_minor,p.title,p.language,p.set_id
   FROM cardyssey_shop.audit_events a LEFT JOIN cardyssey_shop.offers o ON o.id::text=a.entity_id
   LEFT JOIN cardyssey_shop.products p ON p.id=o.product_id
   WHERE a.action='manual_sold' AND a.entity_type='offer' ORDER BY a.created_at DESC LIMIT 500
  ) t`);
  return Response.json(JSON.parse(raw||"[]"),{headers:{"Cache-Control":"no-store"}});
 }catch{return Response.json({error:"bookkeeping_unavailable"},{status:503})}
}
export async function DELETE(request:Request){
 if(!await isShopAdmin())return Response.json({error:"forbidden"},{status:403});
 const origin=request.headers.get("origin");
 if(!origin||![new URL(request.url).origin,process.env.CARDYSSEY_PUBLIC_ORIGIN||"https://cardyssey.de"].includes(origin))return Response.json({error:"origin_mismatch"},{status:403});
 let id:number;try{id=Number((await request.json()).id)}catch{return Response.json({error:"invalid_json"},{status:400})}
 if(!Number.isSafeInteger(id)||id<1)return Response.json({error:"invalid_id"},{status:400});
 try{
  const deleted=await shopSql(`DELETE FROM cardyssey_shop.audit_events WHERE id=${id} AND action='manual_sold' AND entity_type='offer' RETURNING id`);
  if(!deleted)return Response.json({error:"not_found"},{status:404});
  return Response.json({ok:true});
 }catch{return Response.json({error:"delete_failed"},{status:503})}
}
