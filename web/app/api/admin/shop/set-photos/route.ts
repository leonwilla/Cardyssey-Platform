import {randomBytes} from "node:crypto";
import {mkdir,readdir,readFile,writeFile} from "node:fs/promises";
import path from "node:path";
import {isShopAdmin,SHOP_PHOTO_ROOT,validLanguage,validSet,StoredPhoto} from "@/lib/server/shop-photos";
export const runtime="nodejs";
export const dynamic="force-dynamic";
const fail=(error:string,status=400)=>Response.json({error},{status});
function kind(b:Buffer){if(b.length>3&&b[0]===0xff&&b[1]===0xd8&&b[2]===0xff)return {mime:"image/jpeg",ext:"jpg"};
 if(b.length>8&&b.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))return {mime:"image/png",ext:"png"};
 if(b.length>12&&b.toString("ascii",0,4)==="RIFF"&&b.toString("ascii",8,12)==="WEBP")return {mime:"image/webp",ext:"webp"};
 return null;}
export async function GET(request:Request){
 if(!await isShopAdmin())return fail("forbidden",403);
 const u=new URL(request.url),setId=u.searchParams.get("setId")||"",language=u.searchParams.get("language")||"";
 if(!validSet(setId)||!validLanguage(language))return fail("invalid_set");
 const folder=path.join(SHOP_PHOTO_ROOT,language,setId);
 try{
  const files=(await readdir(folder)).filter(n=>n.endsWith(".json")).slice(0,500);
  const photos:StoredPhoto[]=[];
  for(const file of files){try{photos.push(JSON.parse(await readFile(path.join(folder,file),"utf8")))}catch{}}
  photos.sort((a,b)=>b.uploadedAt.localeCompare(a.uploadedAt));
  return Response.json(photos,{headers:{"Cache-Control":"no-store"}});
 }catch(e){if((e as NodeJS.ErrnoException).code==="ENOENT")return Response.json([]);return fail("photo_storage_unavailable",503)}
}
export async function POST(request:Request){
 if(!await isShopAdmin())return fail("forbidden",403);
 const origin=request.headers.get("origin");
 if(!origin||origin!=="https://cardyssey.de"&&origin!==new URL(request.url).origin)return fail("origin_mismatch",403);
 const size=Number(request.headers.get("content-length")||0);
 if(size>12*1024*1024)return fail("file_too_large",413);
 let form:FormData;
 try{form=await request.formData()}catch{return fail("invalid_upload")}
 const setId=String(form.get("setId")||""),language=String(form.get("language")||"");
 const file=form.get("photo");
 if(!validSet(setId)||!validLanguage(language)||!(file instanceof File))return fail("invalid_upload");
 if(file.size<100||file.size>10*1024*1024)return fail("file_too_large",413);
 const bytes=Buffer.from(await file.arrayBuffer());const type=kind(bytes);
 if(!type)return fail("supported_formats_jpg_png_webp",415);
 const id=randomBytes(16).toString("hex"),folder=path.join(SHOP_PHOTO_ROOT,language,setId);
 const photo:StoredPhoto={id,setId,language,name:file.name.slice(0,120),contentType:type.mime,size:bytes.length,uploadedAt:new Date().toISOString()};
 try{
  await mkdir(folder,{recursive:true,mode:0o700});
  await writeFile(path.join(folder,id+"."+type.ext),bytes,{flag:"wx",mode:0o600});
  await writeFile(path.join(folder,id+".json"),JSON.stringify(photo),{flag:"wx",mode:0o600});
  return Response.json(photo,{status:201});
 }catch{return fail("photo_storage_unavailable",503)}
}
