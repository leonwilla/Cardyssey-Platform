import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type RouteContext = {
  params: Promise<{
    key: string;
  }>;
};

export async function PUT(
  request: Request,
  context: RouteContext
) {
  const { key } =
    await context.params;

  const body =
    await request.text();

  const response =
    await authenticatedBackendFetch(
      `/api/v1/collection/${encodeURIComponent(key)}`,
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
    await readBackendJson(response);

  return Response.json(
    data,
    { status: response.status }
  );
}

export async function DELETE(
  _request: Request,
  context: RouteContext
) {
  const { key } =
    await context.params;

  const response =
    await authenticatedBackendFetch(
      `/api/v1/collection/${encodeURIComponent(key)}`,
      {
        method: "DELETE",
      }
    );

  if (response.status === 204) {
    return new Response(
      null,
      { status: 204 }
    );
  }

  const data =
    await readBackendJson(response);

  return Response.json(
    data,
    { status: response.status }
  );
}
