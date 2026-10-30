import {authenticatedBackendFetch} from "@/lib/server/cardyssey-api";
export const dynamic = "force-dynamic";
function safeDestination(raw:string|null):string{
 try{
  const target=new URL(raw||"/collection","https://cardyssey.de");
  if(target.protocol!=="https:"||!["cardyssey.de","shop.cardyssey.de"].includes(target.hostname)||target.port)return "https://cardyssey.de/collection";
  if(target.pathname.startsWith("/api/auth/renew")||target.pathname==="/login")return "https://cardyssey.de/collection";
  return target.toString();
 }catch{return "https://cardyssey.de/collection"}
}
export async function GET(request:Request){
 const url=new URL(request.url);
 const destination=safeDestination(url.searchParams.get("returnTo"));
 const session=await authenticatedBackendFetch("/api/v1/me");
 return new Response(null,{status:303,headers:{"Location":session.ok?destination:"https://cardyssey.de/login","Cache-Control":"no-store"}});
}
