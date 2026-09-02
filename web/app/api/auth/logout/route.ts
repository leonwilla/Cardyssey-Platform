import { cookies } from "next/headers";
import { backendFetch, clearAuthCookies } from "@/lib/server/cardyssey-api";

export async function POST() {
  const jar = await cookies();
  const refreshToken = jar.get("cardyssey_refresh")?.value;

  if (refreshToken) {
    await backendFetch("/api/v1/auth/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken }),
    }).catch(() => null);
  }

  await clearAuthCookies();
  return Response.json({ ok: true });
}
