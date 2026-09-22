import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function GET(
  request: Request
) {
  const url = new URL(request.url);
  const q =
    url.searchParams.get("q") ?? "";

  const response =
    await authenticatedBackendFetch(
      `/api/v1/admin/chat/messages?q=${
        encodeURIComponent(q)
      }`
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}
