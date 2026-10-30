import {readFile} from "node:fs/promises";
import path from "node:path";
import {isShopAdmin,SHOP_PHOTO_ROOT,validPhotoId,validLanguage,validSet,StoredPhoto} from "@/lib/server/shop-photos";
import {shopSql,sqlLiteral} from "@/lib/server/native-shop-db";
export const runtime="nodejs";
export const dynamic="force-dynamic";
export async function GET(_request:Request,context:{params:Promise<{language:string;setId:string;id:string}>}){
 const {language,setId,id}=await context.params;
 if(!validLanguage(language)||!validSet(setId)||!validPhotoId(id))return new Response(null,{status:404});
 try{
  const meta:StoredPhoto=JSON.parse(await readFile(path.join(SHOP_PHOTO_ROOT,language,setId,id+".json"),"utf8"));
  if(meta.id!==id||meta.language!==language||meta.setId!==setId)return new Response(null,{status:404});
  // Unassigned/private uploads are admin-only. Published products may show the actual photo.
  const publicUrl="https://cardyssey.de/api/shop/set-photo/"+language+"/"+setId+"/"+id;
  const found=await shopSql(`SELECT EXISTS(SELECT 1 FROM cardyssey_shop.offer_media m JOIN cardyssey_shop.offers o ON o.id=m.offer_id WHERE m.media_url=${sqlLiteral(publicUrl)} AND o.status='published')`);
  if(found!=="t"&&!await isShopAdmin())return new Response(null,{status:404});
  const ext=meta.contentType==="image/png"?"png":meta.contentType==="image/webp"?"webp":"jpg";
  const data=await readFile(path.join(SHOP_PHOTO_ROOT,language,setId,id+"."+ext));
  return new Response(new Uint8Array(data),{headers:{"Content-Type":meta.contentType,"Content-Disposition":"inline","X-Content-Type-Options":"nosniff","Cache-Control":"private, max-age=300"}});
 }catch{return new Response(null,{status:404})}
}
