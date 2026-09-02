import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function GET() {
  const response =
    await authenticatedBackendFetch("/api/v1/friends");

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}
