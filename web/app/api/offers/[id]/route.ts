import {
  generatedApiError,
  offersApi,
} from "@/lib/server/generated-cardyssey";

type Context = {
  params: Promise<{
    id: string;
  }>;
};

export async function DELETE(
  _request: Request,
  context: Context
) {
  const { id } =
    await context.params;

  try {
    await offersApi()
      .withdrawOffer({
        id,
      });

    return new Response(
      null,
      {
        status: 204,
      }
    );

  } catch (error) {
    return generatedApiError(
      error
    );
  }
}
