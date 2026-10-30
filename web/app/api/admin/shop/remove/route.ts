import {isShopAdmin} from "@/lib/server/shop-photos";
import {shopSql} from "@/lib/server/native-shop-db";
import {cleanupOfferPhotos} from "@/lib/server/shop-photo-cleanup";
export const runtime="nodejs";export const dynamic="force-dynamic";
export async function POST(request:Request){
 if(!await isShopAdmin())return Response.json({error:"forbidden"},{status:403});
 const origin=request.headers.get("origin");
 if(!origin||![new URL(request.url).origin,process.env.CARDYSSEY_PUBLIC_ORIGIN||"https://cardyssey.de"].includes(origin))return Response.json({error:"origin_mismatch"},{status:403});
 let id:number;try{id=Number((await request.json()).offerId)}catch{return Response.json({error:"invalid_json"},{status:400})}
 if(!Number.isSafeInteger(id)||id<1)return Response.json({error:"invalid_offer"},{status:400});
 try{
  const result=await shopSql(`UPDATE cardyssey_shop.offers SET status='archived',version=version+1,updated_at=now() WHERE id=${id} AND status IN ('draft','published') AND reserved_quantity=0 RETURNING id`);
  if(!result)return Response.json({error:"not_found_or_reserved"},{status:409});
  // This action is NOT a sale and MUST NOT be written into the sales ledger.
  let cleanupError=false;try{await cleanupOfferPhotos(id)}catch{cleanupError=true}
  return Response.json({ok:true,id,cleanupWarning:cleanupError});
 }catch{return Response.json({error:"remove_failed"},{status:503})}
}
