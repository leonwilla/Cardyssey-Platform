import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function GET() {
  const response =
    await authenticatedBackendFetch(
      "/api/v1/friends/requests"
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}

export async function POST(request: Request) {
  const body = await request.text();

  const response =
    await authenticatedBackendFetch(
      "/api/v1/friends/requests",
      {
        method: "POST",
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
