import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

function backendPath(request: Request) {
  const requestUrl = new URL(request.url);
  return `/api/v1/chat/groups${requestUrl.search}`;
}

async function forward(
  request: Request,
  method: string,
) {
  const body =
    method === "GET" || method === "DELETE"
      ? undefined
      : await request.arrayBuffer();

  const response =
    await authenticatedBackendFetch(
      backendPath(request),
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

export const GET = (request: Request) =>
  forward(request, "GET");

export const POST = (request: Request) =>
  forward(request, "POST");
