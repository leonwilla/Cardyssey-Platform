import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type Context = {
  params: Promise<{ path: string[] }>;
};

function encoded(path: string[]) {
  return path.map(encodeURIComponent).join("/");
}

async function forward(
  request: Request,
  context: Context,
  method: string,
) {
  const { path } = await context.params;
  const requestUrl = new URL(request.url);
  const target =
    `/api/v1/chat/groups/${encoded(path)}${requestUrl.search}`;

  const body =
    method === "GET" || method === "DELETE"
      ? undefined
      : await request.arrayBuffer();

  const response =
    await authenticatedBackendFetch(
      target,
      {
        method,
        headers: body
          ? {
              "Content-Type":
                request.headers.get("content-type") ??
                "application/json",
            }
          : undefined,
        body: body
          ? Buffer.from(body)
          : undefined,
      }
    );

  if (response.status === 204) {
    return new Response(null, { status: 204 });
  }

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}

export const GET = (
  request: Request,
  context: Context
) => forward(request, context, "GET");

export const POST = (
  request: Request,
  context: Context
) => forward(request, context, "POST");

export const PATCH = (
  request: Request,
  context: Context
) => forward(request, context, "PATCH");

export const PUT = (
  request: Request,
  context: Context
) => forward(request, context, "PUT");

export const DELETE = (
  request: Request,
  context: Context
) => forward(request, context, "DELETE");
