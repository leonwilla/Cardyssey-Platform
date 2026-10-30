import {isShopAdmin,validLanguage,validSet,validPhotoId} from "@/lib/server/shop-photos";
import {deleteUnreferencedPhoto} from "@/lib/server/shop-photo-cleanup";
import {shopSql,sqlLiteral} from "@/lib/server/native-shop-db";
export const runtime="nodejs";export const dynamic="force-dynamic";
export async function DELETE(request:Request){
 if(!await isShopAdmin())return Response.json({error:"forbidden"},{status:403});
 const origin=request.headers.get("origin");
 if(!origin||![new URL(request.url).origin,process.env.CARDYSSEY_PUBLIC_ORIGIN||"https://cardyssey.de"].includes(origin))return Response.json({error:"origin_mismatch"},{status:403});
 let language:string,setId:string,id:string,detach:boolean;
 try{const body=await request.json();language=String(body.language);setId=String(body.setId);id=String(body.id);detach=body.detach===true}catch{return Response.json({error:"invalid_json"},{status:400})}
 if(!validLanguage(language)||!validSet(setId)||!validPhotoId(id))return Response.json({error:"invalid_photo"},{status:400});
 try{
  const url="https://cardyssey.de/api/shop/set-photo/"+language+"/"+setId+"/"+id;
  const count=await shopSql(`SELECT COUNT(*) FROM cardyssey_shop.offer_media WHERE media_url=${sqlLiteral(url)}`);
  if(Number(count)>0&&!detach)return Response.json({error:"photo_in_use"},{status:409});
  if(detach)await shopSql(`DELETE FROM cardyssey_shop.offer_media WHERE media_url=${sqlLiteral(url)}`);
  const deleted=await deleteUnreferencedPhoto(language,setId,id);
  return Response.json({ok:true,deleted});
 }catch{return Response.json({error:"photo_delete_failed"},{status:503})}
}
