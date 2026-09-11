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

  const sourceUrl =
    new URL(request.url);

  const params =
    new URLSearchParams();

  for (
    const key of [
      "language",
      "variantId",
      "variant",
      "condition",
      "market",
    ]
  ) {
    const value =
      sourceUrl.searchParams
        .get(key)
        ?.trim();

    if (value) {
      params.set(
        key,
        value
      );
    }
  }

  const query =
    params.toString();

  const response =
    await authenticatedBackendFetch(
      `/api/v1/pricing/cards/${
        encodeURIComponent(id)
      }${query ? `?${query}` : ""}`
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
