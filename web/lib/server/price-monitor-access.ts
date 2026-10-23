import {authenticatedBackendFetch,readBackendJson} from '@/lib/server/cardyssey-api';
import {withAdminAccess} from '@/lib/server/admin-access';
export async function priceMonitorAllowed(){
 const response=await authenticatedBackendFetch('/api/v1/me');
 if(!response.ok)return false;
 const user=await withAdminAccess(await readBackendJson(response),response.status) as {id?:string;role?:string;canAdmin?:boolean}|null;
 const allowed=(process.env.CARDYSSEY_PRIVATE_USER_IDS||'').split(',').map(s=>s.trim());
 return Boolean(user?.id&&allowed.includes(user.id)&&(user.canAdmin===true||user.role==='ADMIN'||user.role==='FOUNDER'));
}
