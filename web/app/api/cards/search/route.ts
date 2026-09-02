import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function GET(
  request: Request
) {
  const url =
    new URL(request.url);

  const backendParams =
    new URLSearchParams();

  for (
    const key of [
      "q",
      "number",
      "language",
      "limit",
    ]
  ) {
    const value =
      url.searchParams.get(key);

    if (
      value != null &&
      value.trim() !== ""
    ) {
      backendParams.set(
        key,
        value
      );
    }
  }

  const query =
    backendParams.toString();

  const response =
    await authenticatedBackendFetch(
      `/api/v1/cards/search${
        query
          ? `?${query}`
          : ""
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
