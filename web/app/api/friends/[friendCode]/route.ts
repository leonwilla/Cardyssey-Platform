import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type Context = {
  params: Promise<{
    friendCode: string;
  }>;
};

export async function GET(
  _request: Request,
  context: Context
) {
  const { friendCode } =
    await context.params;

  const response =
    await authenticatedBackendFetch(
      `/api/v1/friends/${
        encodeURIComponent(friendCode)
      }/profile`
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}

export async function DELETE(
  _request: Request,
  context: Context
) {
  const { friendCode } =
    await context.params;

  const response =
    await authenticatedBackendFetch(
      `/api/v1/friends/${
        encodeURIComponent(friendCode)
      }`,
      { method: "DELETE" }
    );

  return new Response(null, {
    status: response.status,
  });
}
