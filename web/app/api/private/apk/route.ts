import { readFile } from "node:fs/promises";
import path from "node:path";
import { authenticatedBackendFetch, backendFetch, readBackendJson } from "@/lib/server/cardyssey-api";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request) {
  const bearer = request.headers.get("authorization");
  const me = bearer?.startsWith("Bearer ")
    ? await backendFetch("/api/v1/me", { headers: { Authorization: bearer } })
    : await authenticatedBackendFetch("/api/v1/me");

  if (!me.ok) return new Response("Unauthorized", { status: 401 });
  const user = await readBackendJson(me) as { id?: string } | null;
  const allowed = (process.env.CARDYSSEY_PRIVATE_USER_IDS ?? "")
    .split(",").map(x => x.trim()).filter(Boolean);
  if (!user?.id || !allowed.includes(user.id))
    return new Response("Forbidden", { status: 403 });

  try {
    const apk = await readFile(path.join(process.env.CARDYSSEY_PRIVATE_RELEASE_DIR || "/home/tv/cardshop/web/private-downloads", "cardyssey-latest.apk"));
    return new Response(apk, {
      headers: {
        "Content-Type": "application/vnd.android.package-archive",
        "Content-Disposition": "attachment; filename=cardyssey-latest.apk",
        "Content-Length": String(apk.byteLength),
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
      }
    });
  } catch {
    return new Response("APK unavailable", { status: 503 });
  }
}
