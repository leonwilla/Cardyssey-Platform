import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type Context = {
  params: Promise<{
    friendCode: string;
    messageId: string;
  }>;
};

export async function POST(
  request: Request,
  context: Context
) {
  const {
    friendCode,
    messageId,
  } = await context.params;

  const body =
    await request.text();

  const response =
    await authenticatedBackendFetch(
      `/api/v1/chat/${encodeURIComponent(friendCode)}/messages/${encodeURIComponent(messageId)}/reactions`,
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body,
      }
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}
