import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function POST(request: Request) {
  const body = await request.text();

  const response =
    await authenticatedBackendFetch(
      "/api/v1/cards/recognize",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body,
      }
    );

  const data = await readBackendJson(response);

  return Response.json(data, {
    status: response.status,
  });
}
