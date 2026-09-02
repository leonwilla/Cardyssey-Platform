import {
  generatedApiError,
  offersApi,
} from "@/lib/server/generated-cardyssey";

type Context = {
  params: Promise<{
    id: string;
  }>;
};

export async function POST(
  _request: Request,
  context: Context
) {
  const { id } =
    await context.params;

  try {
    return Response.json(
      await offersApi()
        .acceptOffer({
          id,
        })
    );
  } catch (error) {
    return generatedApiError(
      error
    );
  }
}
