import {authenticatedBackendFetch} from "@/lib/server/cardyssey-api";
import {shopSql} from "@/lib/server/native-shop-db";
export const runtime="nodejs";
export const dynamic="force-dynamic";
export async function GET(request:Request){
 const session=await authenticatedBackendFetch("/api/v1/me");
 if(!session.ok)return Response.json({error:"login_required"},{status:401});
 try{
  const url=new URL(request.url);
  const language=url.searchParams.get("language")||"de";
  if(!["de","en","ja","ko","zh-cn","zh-tw"].includes(language))return Response.json({error:"language"},{status:400});
  const result=await shopSql(`SELECT COALESCE(json_agg(row_to_json(t)),'[]'::json) FROM (
    SELECT o.id,o.sku,p.title,p.card_id,p.set_id,p.language,o.variant,o.condition,o.price_minor,o.stock_quantity-o.reserved_quantity AS available_quantity
    FROM cardyssey_shop.offers o JOIN cardyssey_shop.products p ON p.id=o.product_id
    WHERE o.status='published' AND o.stock_quantity>o.reserved_quantity AND o.price_minor>0
    AND p.language='${language}' ORDER BY p.title,o.id LIMIT 500
   ) t`);
  return Response.json(JSON.parse(result||"[]"),{headers:{"Cache-Control":"private, no-store"}});
 }catch{return Response.json({error:"shop_unavailable"},{status:503})}
}
