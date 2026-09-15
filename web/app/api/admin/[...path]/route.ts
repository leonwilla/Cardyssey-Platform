import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type Context = {
  params: Promise<{
    path: string[];
  }>;
};

function adminPath(
  request: Request,
  path: string[]
) {
  const requestUrl =
    new URL(request.url);

  const encodedPath =
    path
      .map(encodeURIComponent)
      .join("/");

  return `/api/v1/admin/${encodedPath}${requestUrl.search}`;
}

export async function GET(
  request: Request,
  context: Context
) {
  const { path } =
    await context.params;

  const response =
    await authenticatedBackendFetch(
      adminPath(request, path)
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}

export async function DELETE(
  request: Request,
  context: Context
) {
  const { path } =
    await context.params;

  const response =
    await authenticatedBackendFetch(
      adminPath(request, path),
      { method: "DELETE" }
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}
