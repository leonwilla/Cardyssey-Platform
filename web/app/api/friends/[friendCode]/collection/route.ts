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
      `/api/v1/friends/${
        encodeURIComponent(
          friendCode
        )
      }/collection`
    );

  return Response.json(
    await readBackendJson(response),
    {
      status:
        response.status,
    }
  );
}
