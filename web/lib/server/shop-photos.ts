import {authenticatedBackendFetch,readBackendJson} from "@/lib/server/cardyssey-api";
import {withAdminAccess} from "@/lib/server/admin-access";
export async function isShopAdmin():Promise<boolean>{
 const r=await authenticatedBackendFetch("/api/v1/me");
 if(!r.ok)return false;
 const user=await withAdminAccess(await readBackendJson(r),r.status) as {id?:string;role?:string;canAdmin?:boolean}|null;
 const ids=(process.env.CARDYSSEY_PRIVATE_USER_IDS||"").split(",").map(v=>v.trim());
 return !!user?.id&&ids.includes(user.id)&&(user.role==="FOUNDER"||user.role==="ADMIN"||user.canAdmin===true);
}
export const SHOP_PHOTO_ROOT="/home/tv/cardshop/uploads/shop-set-photos";
export const validLanguage=(v:string)=>["de","en","ja","ko","zh-cn","zh-tw"].includes(v);
export const validSet=(v:string)=>/^[a-z0-9_-]{1,100}$/i.test(v);
export const validPhotoId=(v:string)=>/^[a-f0-9]{32}$/.test(v);
export type StoredPhoto={id:string;setId:string;language:string;name:string;contentType:string;size:number;uploadedAt:string};
