import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function GET() {
  const response =
    await authenticatedBackendFetch(
      "/api/v1/me"
    );

  const data =
    await readBackendJson(response);

  return Response.json(
    data,
    { status: response.status }
  );
}

export async function PUT(
  request: Request
) {
  const body =
    await request.text();

  const response =
    await authenticatedBackendFetch(
      "/api/v1/me",
      {
        method: "PUT",
        headers: {
          "Content-Type":
            "application/json",
        },
        body,
      }
    );

  const data =
    await readBackendJson(response);

  return Response.json(
    data,
    { status: response.status }
  );
}
