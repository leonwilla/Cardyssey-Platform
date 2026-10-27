import { authenticatedBackendFetch, readBackendJson } from "@/lib/server/cardyssey-api";
import { withAdminAccess } from "@/lib/server/admin-access";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Payload = {
  cardId:string; setId:string; name:string; setName:string; localId:string;
  language:string; variant:string; condition:string; quantity:number;
  price:string; imageUrl?:string; photoUrl?:string; action:"draft"|"publish"|"unpublish";
};
const host = process.env.CARDYSSEY_WC_URL || process.env.NEXT_PUBLIC_SHOP_URL || "https://shop.cardyssey.de";
const allowedLanguages = new Set(["de","en","ja","ko","zh-cn","zh-tw"]);
const allowedConditions = new Set(["Near Mint","Excellent","Good","Light Played","Played","Poor"]);
const skuPart=(value:string)=>value.normalize("NFKD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]/gi,"-").replace(/-+/g,"-").replace(/^-|-$/g,"").toUpperCase();
const clean=(v:unknown,max=160)=>typeof v==="string"?v.trim().slice(0,max):"";
const permittedImage=(value:string)=>{try{const url=new URL(value);return url.protocol==="https:"&&!url.username&&!url.password&&!["localhost","127.0.0.1","::1"].includes(url.hostname)&&!url.hostname.endsWith(".local");}catch{return false}};
async function permitted(){
 const response=await authenticatedBackendFetch("/api/v1/me");
 if(!response.ok)return false;
 const u=await withAdminAccess(await readBackendJson(response),response.status) as {id?:string;role?:string;canAdmin?:boolean}|null;
 const ids=(process.env.CARDYSSEY_PRIVATE_USER_IDS||"").split(",").map(x=>x.trim());
 return !!u?.id&&ids.includes(u.id)&&(u.role==="FOUNDER"||u.role==="ADMIN"||u.canAdmin===true);
}
export async function POST(request:Request){
 if(!await permitted())return Response.json({error:"forbidden"},{status:403});
 if(request.headers.get("origin")!==new URL(request.url).origin)return Response.json({error:"origin_mismatch"},{status:403});
 const key=process.env.CARDYSSEY_WC_CONSUMER_KEY;
 const secret=process.env.CARDYSSEY_WC_CONSUMER_SECRET;
 if(!key||!secret)return Response.json({error:"woocommerce_not_configured"},{status:503});
 let input:Payload;
 try {input=await request.json() as Payload;}catch{return Response.json({error:"invalid_json"},{status:400})}
 const cardId=clean(input.cardId,100),setId=clean(input.setId,100),name=clean(input.name),setName=clean(input.setName),localId=clean(input.localId,40);
 const language=clean(input.language,12),variant=clean(input.variant,50),condition=clean(input.condition,30),photoUrl=clean(input.photoUrl,1000),imageUrl=clean(input.imageUrl,1000);
 const quantity=input.quantity,price=Number(String(input.price).replace(",","."));
 if(!cardId||!setId||!name||!setName||!localId||!variant||!allowedLanguages.has(language)||!allowedConditions.has(condition)||!Number.isInteger(quantity)||quantity<0||quantity>100000||!["draft","publish","unpublish"].includes(input.action)){
   return Response.json({error:"invalid_listing"},{status:400});
 }
 if(input.action==="publish"&&(quantity<1||!Number.isFinite(price)||price<=0))return Response.json({error:"stock_and_price_required"},{status:400});
 if((photoUrl&&!permittedImage(photoUrl))||(imageUrl&&!permittedImage(imageUrl)))return Response.json({error:"invalid_image_url"},{status:400});
 // Explicitly opt in to writes only after WooCommerce credentials, image rights and integration are verified.
 if(process.env.CARDYSSEY_WC_SYNC_ENABLED!=="true")return Response.json({error:"sync_disabled_until_live_validation"},{status:503});
 const shop=new URL(host);
 if(shop.protocol!=="https:")return Response.json({error:"insecure_shop_endpoint"},{status:503});
 const sku="CDY-"+skuPart([language,setId,cardId,variant,condition].join("-"));
 const auth="Basic "+Buffer.from(key+":"+secret).toString("base64");
 const api=new URL("/wp-json/wc/v3/products",shop);
 const headers={Authorization:auth,"Content-Type":"application/json",Accept:"application/json"};
 try{
  const lookup=new URL(api);lookup.searchParams.set("sku",sku);lookup.searchParams.set("per_page","2");
  const previous=await fetch(lookup,{headers,cache:"no-store",signal:AbortSignal.timeout(12000)});
  if(!previous.ok)return Response.json({error:"woocommerce_lookup_failed",status:previous.status},{status:502});
  const matches=await previous.json() as {id:number;sku:string}[];
  if(!Array.isArray(matches)||matches.length>1||matches.some(m=>m.sku!==sku))return Response.json({error:"sku_collision_or_invalid_response"},{status:409});
  const existing=matches[0];
  const image=photoUrl||imageUrl;
  const product={
   type:"simple",sku,name:[name,localId,setName,variant,condition].join(" · "),
   status:input.action==="publish"?"publish":"draft",
   catalog_visibility:"visible",manage_stock:true,stock_quantity:input.action==="unpublish"?0:quantity,
   stock_status:input.action==="unpublish"||quantity===0?"outofstock":"instock",
   backorders:"no",sold_individually:false,
   regular_price:Number.isFinite(price)&&price>0?price.toFixed(2):"",
   description:(photoUrl?"Eigenes Foto des angebotenen Exemplars. ":"Referenzbild, nicht das tatsächlich angebotene Exemplar. ")+"Zustand: "+condition+".",
   attributes:[{name:"Sprache",visible:true,variation:false,options:[language]},{name:"Variante",visible:true,variation:false,options:[variant]},{name:"Zustand",visible:true,variation:false,options:[condition]}],
   meta_data:[{key:"_cardyssey_card_id",value:cardId},{key:"_cardyssey_set_id",value:setId},{key:"_cardyssey_language",value:language}],
   ...(image?{images:[{src:image}]}:{})
  };
  const target=existing?new URL("/wp-json/wc/v3/products/"+existing.id,shop):api;
  const result=await fetch(target,{method:existing?"PUT":"POST",headers,body:JSON.stringify(product),signal:AbortSignal.timeout(20000),cache:"no-store"});
  if(!result.ok)return Response.json({error:"woocommerce_write_failed",status:result.status},{status:502});
  const saved=await result.json() as {id:number;status:string;permalink?:string;stock_quantity?:number};
  return Response.json({id:saved.id,sku,status:saved.status,stock:saved.stock_quantity,permalink:saved.permalink},{headers:{"Cache-Control":"no-store"}});
 }catch{return Response.json({error:"woocommerce_unavailable"},{status:502})}
}
