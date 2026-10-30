import {authenticatedBackendFetch,readBackendJson} from "@/lib/server/cardyssey-api";
import {withAdminAccess} from "@/lib/server/admin-access";
import {shopSql,sqlLiteral} from "@/lib/server/native-shop-db";
export const runtime="nodejs";
export const dynamic="force-dynamic";

type ProductInput={cardId:string;setId:string;name:string;language:string;variant:string;condition:string;quantity:number;price:string;photoUrl?:string;imageUrl?:string;action:"draft"|"publish"|"unpublish"};
const languages=new Set(["de","en","ja","ko","zh-cn","zh-tw"]);
const conditions=new Set(["Near Mint","Excellent","Good","Light Played","Played","Poor"]);
const clean=(v:unknown,max=150)=>typeof v==="string"?v.trim().slice(0,max):"";
async function isAdmin(){
 const r=await authenticatedBackendFetch("/api/v1/me");
 if(!r.ok)return false;
 const user=await withAdminAccess(await readBackendJson(r),r.status) as {id?:string;role?:string;canAdmin?:boolean}|null;
 const allowed=(process.env.CARDYSSEY_PRIVATE_USER_IDS||"").split(",").map(v=>v.trim());
 return !!user?.id&&allowed.includes(user.id)&&(user.role==="FOUNDER"||user.role==="ADMIN"||user.canAdmin===true);
}
function rejection(message:string,status=400){return Response.json({error:message},{status})}
export async function GET(){
 if(!await isAdmin())return rejection("forbidden",403);
 try{
  const result=await shopSql(`SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json) FROM (
   SELECT o.id,o.sku,p.title,p.set_id,p.card_id,p.language,o.variant,o.condition,o.price_minor,o.stock_quantity,o.status,o.updated_at,(SELECT m.media_url FROM cardyssey_shop.offer_media m WHERE m.offer_id=o.id AND m.is_owned_photo ORDER BY m.position,m.id LIMIT 1) AS photo_url, (SELECT count(*) FROM cardyssey_shop.offer_media m WHERE m.offer_id=o.id AND m.is_owned_photo) AS photo_count
   FROM cardyssey_shop.offers o JOIN cardyssey_shop.products p ON p.id=o.product_id
   ORDER BY o.updated_at DESC LIMIT 500
  ) t`);
  return Response.json(JSON.parse(result||"[]"),{headers:{"Cache-Control":"no-store"}});
 }catch{return rejection("native_shop_unavailable",503)}
}
export async function POST(request:Request){
 if(!await isAdmin())return rejection("forbidden",403);
 const origin=request.headers.get("origin");
 // Public origin differs from internal Next.js URL behind the reverse proxy.
 // Accept only the explicitly configured public Cardyssey origin (or same-origin locally).
 const allowedOrigins=new Set([new URL(request.url).origin,process.env.CARDYSSEY_PUBLIC_ORIGIN||"https://cardyssey.de"]);
 if(!origin||!allowedOrigins.has(origin))return rejection("origin_mismatch",403);
 let data:ProductInput;
 try{data=await request.json()}catch{return rejection("invalid_json")}
 const cardId=clean(data.cardId,100),setId=clean(data.setId,100),name=clean(data.name),language=clean(data.language,12),variant=clean(data.variant,60),condition=clean(data.condition,30);
 const quantity=data.quantity;
 if(!cardId||!setId||!name||!languages.has(language)||!variant||!conditions.has(condition)||!Number.isInteger(quantity)||quantity<0||quantity>100000||!["draft","publish","unpublish"].includes(data.action))return rejection("invalid_listing");
 const raw=String(data.price||"").trim().replace(",",".");
 if(raw&&!/^(?:0|[1-9]\d{0,7})(?:\.\d{1,2})?$/.test(raw))return rejection("invalid_price");
 const priceMinor=raw?Math.round(Number(raw)*100):null;
 if(data.action==="publish"&&(!priceMinor||quantity===0))return rejection("stock_and_price_required");
 const photoUrl=clean(data.photoUrl,1800);
 const imageUrl=clean(data.imageUrl,1800);
 const isSafeImage=(url:string)=>{if(!url)return true;try{const parsed=new URL(url);return parsed.protocol==="https:"&&!parsed.username&&!parsed.password&&url.length<1800}catch{return false}};
 if(!isSafeImage(photoUrl)||!isSafeImage(imageUrl))return rejection("invalid_image_url");
 const sku="CDY-"+Buffer.from(JSON.stringify([language,setId,cardId,variant,condition])).toString("hex").toUpperCase();
 if(sku.length>500)return rejection("sku_too_long");
 const q=sqlLiteral;
 const productQuery=`INSERT INTO cardyssey_shop.products (type,card_id,set_id,language,title)
 VALUES ('card',${q(cardId)},${q(setId)},${q(language)},${q(name)})
 ON CONFLICT (card_id,set_id,language) DO UPDATE SET title=EXCLUDED.title
 RETURNING id`;
 try{
  const productId=Number(await shopSql(productQuery));
  if(!Number.isSafeInteger(productId)||productId<1)throw Error("invalid_product_id");
  const nextStatus=data.action==="publish"?"published":"draft";
  const price=priceMinor===null?"NULL":String(priceMinor);
  // INSERT/UPDATE is idempotent by SKU and cannot create duplicate saleable listings.
  const result=await shopSql(`INSERT INTO cardyssey_shop.offers(product_id,sku,variant,condition,price_minor,stock_quantity,status)
  VALUES (${productId},${q(sku)},${q(variant)},${q(condition)},${price},${quantity},${q(nextStatus)})
  ON CONFLICT(sku) DO UPDATE SET price_minor=EXCLUDED.price_minor,stock_quantity=EXCLUDED.stock_quantity,status=EXCLUDED.status,version=cardyssey_shop.offers.version+1,updated_at=now()
  RETURNING id`);
  const offerId=Number(result);
  if(!Number.isSafeInteger(offerId)||offerId<1)throw Error("invalid_offer_id");
  // The admin manages a single primary media record per offer. Reference artwork
  // is explicitly distinguished from a photo of the actual item.
  const media=photoUrl||imageUrl;
  // Never erase set-uploaded pictures when adjusting stock, price or status.
  // Reference images are replaceable; uploaded photos remain attached.
  if(media){
    await shopSql(`INSERT INTO cardyssey_shop.offer_media(offer_id,media_url,is_owned_photo,rights_verified,position)
    SELECT ${offerId},${q(media)},${photoUrl?"TRUE":"FALSE"},FALSE,0
    WHERE NOT EXISTS(SELECT 1 FROM cardyssey_shop.offer_media WHERE offer_id=${offerId} AND media_url=${q(media)})`);
  }
  return Response.json({ok:true,id:offerId,sku,status:nextStatus});
 }catch{return rejection("native_shop_write_failed",503)}
}
