import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const language =
    url.searchParams.get("language")?.trim() || "de";

  const response =
    await authenticatedBackendFetch(
      `/api/v1/sets?language=${encodeURIComponent(language)}`
    );

  const data = await readBackendJson(response);

  return Response.json(data, {
    status: response.status,
  });
}
