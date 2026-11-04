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

  // TCGdex returns the expansion catalog chronologically (oldest first).
  // Present newest expansions first to every web dropdown and catalog consumer.
  // Preserve upstream errors untouched.
  return Response.json(response.ok && Array.isArray(data) ? [...data].reverse() : data, {
    status: response.status,
  });
}
