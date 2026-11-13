import {
  authenticatedBackendFetch,
  clearAuthCookies,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function POST(request: Request) {
  // SameSite HttpOnly cookies and JSON-only requests prevent ordinary
  // cross-site form submissions. The authenticated backend checks the user.
  const body = await request.json().catch(() => null);
  if (
    !body ||
    typeof body.currentPassword !== "string" ||
    typeof body.newPassword !== "string" ||
    body.currentPassword.length > 128 ||
    body.newPassword.length < 12 ||
    body.newPassword.length > 128
  ) {
    return Response.json({ error: "invalid_password" }, { status: 400 });
  }

  try {
    const response = await authenticatedBackendFetch("/api/v1/me/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        currentPassword: body.currentPassword,
        newPassword: body.newPassword,
      }),
    });

    if (response.ok) {
      await clearAuthCookies();
      return new Response(null, { status: 204 });
    }

    return Response.json(await readBackendJson(response), {
      status: response.status,
    });
  } catch {
    return Response.json({ error: "server_unavailable" }, { status: 503 });
  }
}
