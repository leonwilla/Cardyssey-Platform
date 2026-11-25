import {authenticatedBackendFetch,readBackendJson} from '@/lib/server/cardyssey-api';

// Cardmarket price chart of one card variant; days = 7, 30, 90, 365 or 0 (all).
export async function GET(request:Request, context:{params:Promise<{id:string}>}) {
  const {id}=await context.params;
  if(!/^[a-zA-Z0-9_-]{2,90}$/.test(id))return Response.json({error:'invalid_card_id'},{status:400});
  const url=new URL(request.url);
  const days=url.searchParams.get('days')||'30';
  if(!['0','7','30','90','365'].includes(days))return Response.json({error:'invalid_range'},{status:400});
  const params=new URLSearchParams({language:url.searchParams.get('language')||'de',variantId:url.searchParams.get('variantId')||'',days});
  const response=await authenticatedBackendFetch(`/api/v1/pricing/tcg-history/${encodeURIComponent(id)}?${params.toString()}`);
  const data=await readBackendJson(response);
  return Response.json(data,{status:response.status,headers:{'Cache-Control':'private, no-store'}});
}
