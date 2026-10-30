import {readFile} from "node:fs/promises";
import path from "node:path";
import {isShopAdmin,SHOP_PHOTO_ROOT,validPhotoId,StoredPhoto} from "@/lib/server/shop-photos";
import {shopSql,sqlLiteral} from "@/lib/server/native-shop-db";
export const runtime="nodejs";
export const dynamic="force-dynamic";
export async function POST(request:Request){
 if(!await isShopAdmin())return Response.json({error:"forbidden"},{status:403});
 const origin=request.headers.get("origin");
 if(!origin||origin!=="https://cardyssey.de"&&origin!==new URL(request.url).origin)return Response.json({error:"origin_mismatch"},{status:403});
 let offerId:number,photoId:string,role:string;
 try{const body=await request.json();offerId=Number(body.offerId);photoId=String(body.photoId);role=String(body.role||"detail")}catch{return Response.json({error:"invalid_json"},{status:400})}
 if(!Number.isSafeInteger(offerId)||offerId<1||!validPhotoId(photoId)||!["front","back","detail"].includes(role))return Response.json({error:"invalid_assignment"},{status:400});
 try{
  const offer=await shopSql(`SELECT p.language||'|'||p.set_id FROM cardyssey_shop.offers o JOIN cardyssey_shop.products p ON p.id=o.product_id WHERE o.id=${offerId} LIMIT 1`);
  const [language,setId]=offer.split("|");
  if(!language||!setId)return Response.json({error:"offer_not_found"},{status:404});
  const meta:StoredPhoto=JSON.parse(await readFile(path.join(SHOP_PHOTO_ROOT,language,setId,photoId+".json"),"utf8"));
  if(meta.id!==photoId||meta.language!==language||meta.setId!==setId)return Response.json({error:"wrong_set"},{status:400});
  const url="https://cardyssey.de/api/shop/set-photo/"+language+"/"+setId+"/"+photoId;
  const q=sqlLiteral;
  const position=role==="front"?0:role==="back"?10:20;
  await shopSql(`INSERT INTO cardyssey_shop.offer_media(offer_id,media_url,is_owned_photo,rights_verified,position)
  SELECT ${offerId},${q(url)},TRUE,TRUE,${position}
  WHERE NOT EXISTS(SELECT 1 FROM cardyssey_shop.offer_media WHERE offer_id=${offerId} AND media_url=${q(url)})`);
  return Response.json({ok:true,url});
 }catch{return Response.json({error:"assignment_failed"},{status:503})}
}
