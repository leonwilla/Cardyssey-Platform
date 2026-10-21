import { authenticatedBackendFetch, readBackendJson } from "@/lib/server/cardyssey-api";
export const dynamic = "force-dynamic";
export async function GET() {
  const response = await authenticatedBackendFetch("/api/v1/me");
  if (!response.ok) return new Response(null, {status: 401, headers:{"Cache-Control":"no-store"}});
  const user = await readBackendJson(response) as {id?:string}|null;
  const allowed = (process.env.CARDYSSEY_PRIVATE_USER_IDS ?? "").split(",").map(x=>x.trim()).filter(Boolean);
  const ok = !!user?.id && allowed.includes(user.id);
  return new Response(null, {status:ok?204:403, headers:{"Cache-Control":"no-store"}});
}
