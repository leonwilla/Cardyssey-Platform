import {authenticatedBackendFetch,readBackendJson} from '@/lib/server/cardyssey-api';

export async function GET(request:Request, context:{params:Promise<{id:string}>}) {
  const {id}=await context.params;
  if(!/^[a-zA-Z0-9_-]{2,90}$/.test(id))return Response.json({error:'invalid_card_id'},{status:400});
  const url=new URL(request.url);
  const language=url.searchParams.get('language')||'de';
  const variantId=url.searchParams.get('variantId')||'';
  const params=new URLSearchParams({language,variantId});
  const response=await authenticatedBackendFetch(`/api/v1/pricing/history/${encodeURIComponent(id)}?${params.toString()}`);
  const data=await readBackendJson(response);
  return Response.json(data,{status:response.status,headers:{'Cache-Control':'private, no-store'}});
}
