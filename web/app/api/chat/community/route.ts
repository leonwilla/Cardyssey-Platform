import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const response =
    await authenticatedBackendFetch(
      `/api/v1/chat/community${url.search}`
    );

  if (response.status === 204) {
    return new Response(null, { status: 204 });
  }

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}
