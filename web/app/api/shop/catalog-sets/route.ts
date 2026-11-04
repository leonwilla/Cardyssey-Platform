import {shopSql,sqlLiteral} from "@/lib/server/native-shop-db";
export const runtime="nodejs";
export const dynamic="force-dynamic";
const languages=new Set(["de","en","ja","ko","zh-cn","zh-tw"]);
export async function GET(request:Request){
 const language=new URL(request.url).searchParams.get("language")||"de";
 if(!languages.has(language))return Response.json({error:"invalid_language"},{status:400});
 try{
  const sql=`SELECT COALESCE(json_agg(row_to_json(t)),'[]'::json) FROM (
    SELECT published.set_id AS id,COALESCE(s.name,published.set_id) AS name,
      s.logo_source_url AS logo,s.symbol_source_url AS symbol,
      s.official_count AS "officialCount",s.total_count AS "totalCount",
      published.offer_count AS "offerCount"
    FROM (
      SELECT COALESCE(p.set_id,p.associated_set_id) AS set_id,COUNT(*) AS offer_count
      FROM cardyssey_shop.offers o JOIN cardyssey_shop.products p ON p.id=o.product_id
      WHERE o.status='published' AND o.stock_quantity>o.reserved_quantity AND o.price_minor>0
        AND COALESCE(p.language,p.associated_language)=${sqlLiteral(language)}
        AND COALESCE(p.set_id,p.associated_set_id) IS NOT NULL
      GROUP BY COALESCE(p.set_id,p.associated_set_id)
    ) published LEFT JOIN public.catalog_sets_mirror s ON s.set_id=published.set_id AND s.language_code=${sqlLiteral(language)}
    ORDER BY COALESCE(s.name,published.set_id) LIMIT 500
  ) t`;
  return Response.json(JSON.parse(await shopSql(sql)||"[]"),{headers:{"Cache-Control":"private, no-store"}});
 }catch{return Response.json({error:"catalog_unavailable"},{status:503})}
}
