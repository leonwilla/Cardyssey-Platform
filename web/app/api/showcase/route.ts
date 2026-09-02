import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function GET() {
  const response =
    await authenticatedBackendFetch(
      "/api/v1/me/showcase"
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}

export async function PUT(
  request: Request
) {
  const body = await request.text();

  const response =
    await authenticatedBackendFetch(
      "/api/v1/me/showcase",
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body,
      }
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}
