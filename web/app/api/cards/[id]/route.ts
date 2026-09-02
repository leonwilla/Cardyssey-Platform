import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type RouteContext = {
  params: Promise<{
    id: string;
  }>;
};

export async function GET(
  request: Request,
  context: RouteContext
) {
  const { id } =
    await context.params;

  const url =
    new URL(request.url);

  const language =
    url.searchParams
      .get("language")
      ?.trim()
      .toLowerCase() ||
    "de";

  const response =
    await authenticatedBackendFetch(
      `/api/v1/cards/${
        encodeURIComponent(id)
      }?language=${
        encodeURIComponent(
          language
        )
      }`
    );

  const data =
    await readBackendJson(
      response
    );

  return Response.json(
    data,
    {
      status:
        response.status,
    }
  );
}
