import {readdir,readFile,unlink} from "node:fs/promises";
import path from "node:path";
import {SHOP_PHOTO_ROOT,validPhotoId,validLanguage,validSet,StoredPhoto} from "@/lib/server/shop-photos";
import {shopSql,sqlLiteral} from "@/lib/server/native-shop-db";
export function imageUrl(language:string,setId:string,id:string){return "https://cardyssey.de/api/shop/set-photo/"+language+"/"+setId+"/"+id}
export async function deleteUnreferencedPhoto(language:string,setId:string,id:string){
 if(!validLanguage(language)||!validSet(setId)||!validPhotoId(id))throw Error("invalid_photo");
 const url=imageUrl(language,setId,id);
 const inUse=await shopSql(`SELECT EXISTS(SELECT 1 FROM cardyssey_shop.offer_media WHERE media_url=${sqlLiteral(url)})`);
 if(inUse==="t")return false;
 const dir=path.join(SHOP_PHOTO_ROOT,language,setId);
 let meta:StoredPhoto;
 try{meta=JSON.parse(await readFile(path.join(dir,id+".json"),"utf8")))}catch{return false}
 const ext=meta.contentType==="image/png"?"png":meta.contentType==="image/webp"?"webp":"jpg";
 await unlink(path.join(dir,id+"."+ext));
 await unlink(path.join(dir,id+".json"));
 return true;
}
export async function cleanupOfferPhotos(offerId:number){
 const rows=await shopSql(`SELECT COALESCE(json_agg(media_url),'[]'::json) FROM cardyssey_shop.offer_media WHERE offer_id=${offerId} AND is_owned_photo`);
 const urls=JSON.parse(rows||"[]") as string[];
 await shopSql(`DELETE FROM cardyssey_shop.offer_media WHERE offer_id=${offerId}`);
 let removed=0;
 for(const url of urls){
  try{const u=new URL(url);const parts=u.pathname.split("/");if(u.hostname==="cardyssey.de"&&parts.length===7&&parts[1]==="api"&&parts[2]==="shop"&&parts[3]==="set-photo"){if(await deleteUnreferencedPhoto(parts[4],parts[5],parts[6]))removed++}}catch{}
 }
 return removed;
}
