import { readFile } from "node:fs/promises";
import path from "node:path";
import { backendFetch } from "@/lib/server/cardyssey-api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Native Android clients authenticate with the same backend session as the web. */
export async function GET(request: Request) {
  const bearer = request.headers.get("authorization");
  if (!bearer?.startsWith("Bearer ")) {
    return new Response("Unauthorized", { status: 401 });
  }
  const me = await backendFetch("/api/v1/me", {
    headers: { Authorization: bearer },
  });
  if (!me.ok) return new Response("Unauthorized", { status: 401 });
  const user = await me.json() as { id?: string };
  const allowed = (process.env.CARDYSSEY_PRIVATE_USER_IDS ?? "")
    .split(",").map(id => id.trim()).filter(Boolean);
  if (!user?.id || !allowed.includes(user.id)) {
    return new Response("Forbidden", { status: 403 });
  }

  try {
    const raw = await readFile(
      path.join(process.env.CARDYSSEY_PRIVATE_RELEASE_DIR || "/home/tv/cardshop/web/private-downloads", "cardyssey-version.json"),
      "utf8"
    );
    const metadata = JSON.parse(raw) as Record<string, unknown>;
    if (
      typeof metadata.versionCode !== "number" ||
      typeof metadata.versionName !== "string" ||
      typeof metadata.sha256 !== "string" ||
      !/^[a-f0-9]{64}$/i.test(metadata.sha256)
    ) throw new Error("Invalid metadata");
    return Response.json({
      ...metadata,
      apkUrl: "https://cardyssey.de/api/private/apk",
    }, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return new Response("Release unavailable", { status: 503 });
  }
}
