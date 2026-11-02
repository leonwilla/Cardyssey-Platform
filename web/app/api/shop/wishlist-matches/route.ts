import {authenticatedBackendFetch, readBackendJson} from "@/lib/server/cardyssey-api";
import {shopSql} from "@/lib/server/native-shop-db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
type Wish = {cardId?:string;setId?:string|null;languageCode?:string;variantId?:string|null;variantType?:string|null;variantSubtype?:string|null;name?:string;priority?:string};
type Offer = {id:number;card_id:string;set_id:string;language:string;variant:string;condition:string;price_minor:number;available_quantity:number;title?:string;image_url?:string|null};
export async function GET() {
  const me=await authenticatedBackendFetch("/api/v1/me");
  if (!me.ok) return Response.json({error:"login_required"},{status:401});
  const wishlist=await authenticatedBackendFetch("/api/v1/wishlist");
  if (!wishlist.ok) return Response.json({error:"wishlist_unavailable"},{status:502});
  const raw=await readBackendJson(wishlist);
  const wishes:Wish[]=Array.isArray(raw)?raw:[];
  try {
    const sql=`SELECT COALESCE(json_agg(row_to_json(t)),'[]'::json) FROM (
      SELECT o.id,p.title,p.card_id,p.set_id,p.language,o.variant,o.condition,o.price_minor,
      o.stock_quantity-o.reserved_quantity AS available_quantity,
      (SELECT m.media_url FROM cardyssey_shop.offer_media m WHERE m.offer_id=o.id ORDER BY m.is_owned_photo DESC,m.position,m.id LIMIT 1) AS image_url
      FROM cardyssey_shop.offers o JOIN cardyssey_shop.products p ON p.id=o.product_id
      WHERE o.status='published' AND o.stock_quantity>o.reserved_quantity AND o.price_minor>0
      ORDER BY o.id LIMIT 2000) t`;
    const offers:Offer[]=JSON.parse(await shopSql(sql)||"[]");
    const results=offers.flatMap(offer=>{
      const wish=wishes.find(w=>w.cardId===offer.card_id && w.languageCode?.toLowerCase()===offer.language.toLowerCase() && (!w.setId || w.setId===offer.set_id));
      if(!wish)return [];
      // Matching the card alone does not certify a particular foil/printing.
      const requested=[wish.variantId,wish.variantType,wish.variantSubtype].filter(Boolean).map(v=>String(v).toLowerCase());
      const exactVariant=requested.length===0 || requested.some(v=>v===offer.variant.toLowerCase());
      return [{...offer,wishlistName:wish.name||offer.title,priority:wish.priority||"MEDIUM",variantVerified:exactVariant}];
    });
    results.sort((a,b)=>Number(b.variantVerified)-Number(a.variantVerified) || Number(b.priority==="HIGH")-Number(a.priority==="HIGH") || a.price_minor-b.price_minor);
    return Response.json({wishlistCount:wishes.length,matches:results},{headers:{"Cache-Control":"private, no-store"}});
  } catch {return Response.json({error:"matching_unavailable"},{status:503});}
}
