import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

type Context = {
  params: Promise<{
    friendCode: string;
  }>;
};

export async function GET(
  _request: Request,
  context: Context
) {
  const { friendCode } =
    await context.params;

  const response =
    await authenticatedBackendFetch(
      `/api/v1/chat/${
        encodeURIComponent(friendCode)
      }/messages`
    );

  return Response.json(
    await readBackendJson(response),
    { status: response.status }
  );
}

export async function POST(
  request: Request,
  context: Context
) {
  const { friendCode } =
    await context.params;

  const response =
    await authenticatedBackendFetch(
      `/api/v1/chat/${
        encodeURIComponent(friendCode)
      }/messages`,
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
