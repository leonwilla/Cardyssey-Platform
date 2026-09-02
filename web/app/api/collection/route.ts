import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function GET() {
  const response =
    await authenticatedBackendFetch(
      "/api/v1/collection"
    );

  const data =
    await readBackendJson(response);

  return Response.json(
    data,
    { status: response.status }
  );
}

export async function POST(
  request: Request
) {
  const body =
    await request.text();

  const response =
    await authenticatedBackendFetch(
      "/api/v1/collection",
      {
        method: "POST",
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
