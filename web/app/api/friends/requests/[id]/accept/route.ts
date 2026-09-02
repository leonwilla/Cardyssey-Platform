import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type Context = {
  params: Promise<{ id: string }>;
};

export async function POST(
  _request: Request,
  context: Context
) {
  const { id } = await context.params;

  const response =
    await authenticatedBackendFetch(
      `/api/v1/friends/requests/${encodeURIComponent(id)}/accept`,
      { method: "POST" }
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}
