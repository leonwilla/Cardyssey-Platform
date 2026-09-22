import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type Context = {
  params: Promise<{
    id: string;
  }>;
};

export async function POST(
  request: Request,
  context: Context
) {
  const { id } =
    await context.params;

  const response =
    await authenticatedBackendFetch(
      `/api/v1/chat/messages/${
        encodeURIComponent(id)
      }/report`,
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body: await request.text(),
      }
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}
