import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function PUT(
  request: Request
) {
  const body =
    await request.arrayBuffer();

  const response =
    await authenticatedBackendFetch(
      "/api/v1/me/avatar",
      {
        method: "PUT",
        headers: {
          "Content-Type":
            "application/octet-stream",
        },
        body,
      }
    );

  const data =
    await readBackendJson(response);

  return Response.json(
    data,
    { status: response.status }
  );
}

export async function DELETE() {
  const response =
    await authenticatedBackendFetch(
      "/api/v1/me/avatar",
      {
        method: "DELETE",
      }
    );

  const data =
    await readBackendJson(response);

  return Response.json(
    data,
    { status: response.status }
  );
}
