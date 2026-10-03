import {
  authenticatedBackendFetch,
  clearAuthCookies,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

import {
  withAdminAccess,
} from "@/lib/server/admin-access";

export async function GET() {
  const response =
    await authenticatedBackendFetch(
      "/api/v1/me"
    );

  const data =
    await withAdminAccess(
      await readBackendJson(response),
      response.status
    );

  return Response.json(
    data,
    { status: response.status }
  );
}

export async function PUT(
  request: Request
) {
  const body =
    await request.text();

  const response =
    await authenticatedBackendFetch(
      "/api/v1/me",
      {
        method: "PUT",
        headers: {
          "Content-Type":
            "application/json",
        },
        body,
      }
    );

  const data =
    await withAdminAccess(
      await readBackendJson(response),
      response.status
    );

  return Response.json(
    data,
    { status: response.status }
  );
}


export async function DELETE() {
  const response = await authenticatedBackendFetch(
    "/api/v1/me",
    { method: "DELETE" }
  );

  if (response.ok) {
    await clearAuthCookies();
  }

  if (response.status === 204) {
    return new Response(null, { status: 204 });
  }

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}
