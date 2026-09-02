import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type Context = {
  params: Promise<{ id: string }>;
};

export async function GET(
  request: Request,
  context: Context
) {
  const { id } = await context.params;
  const url = new URL(request.url);

  const language =
    url.searchParams.get("language")?.trim() || "de";

  const response =
    await authenticatedBackendFetch(
      `/api/v1/sets/${encodeURIComponent(id)}?language=${encodeURIComponent(language)}`
    );

  const data = await readBackendJson(response);

  return Response.json(data, {
    status: response.status,
  });
}
