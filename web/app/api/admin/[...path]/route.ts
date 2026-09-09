import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type Context = {
  params: Promise<{
    path: string[];
  }>;
};

export async function GET(
  request: Request,
  context: Context
) {
  const { path } =
    await context.params;

  const requestUrl =
    new URL(request.url);

  const encodedPath =
    path
      .map(encodeURIComponent)
      .join("/");

  const response =
    await authenticatedBackendFetch(
      `/api/v1/admin/${encodedPath}${
        requestUrl.search
      }`
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}
