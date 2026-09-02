import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type Context = {
  params: Promise<{
    id: string;
  }>;
};

export async function PUT(
  request: Request,
  context: Context
) {
  const { id } = await context.params;

  const body = await request.text();

  const response =
    await authenticatedBackendFetch(
      `/api/v1/selling/${
        encodeURIComponent(id)
      }`,
      {
        method: "PUT",
        headers: {
          "Content-Type":
            "application/json",
        },
        body,
      }
    );

  if (response.status === 204) {
    return new Response(null, {
      status: 204,
    });
  }

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}

export async function DELETE(
  _request: Request,
  context: Context
) {
  const { id } = await context.params;

  const response =
    await authenticatedBackendFetch(
      `/api/v1/selling/${
        encodeURIComponent(id)
      }`,
      {
        method: "DELETE",
      }
    );

  return new Response(null, {
    status: response.status,
  });
}
