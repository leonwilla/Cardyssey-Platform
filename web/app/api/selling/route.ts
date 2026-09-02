import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function GET() {
  const response =
    await authenticatedBackendFetch(
      "/api/v1/selling"
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}

export async function POST(
  request: Request
) {
  const body = await request.text();

  const response =
    await authenticatedBackendFetch(
      "/api/v1/selling",
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body,
      }
    );

  if (response.status === 201) {
    return new Response(null, {
      status: 201,
    });
  }

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}
