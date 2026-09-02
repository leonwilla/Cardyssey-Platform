import {
  authenticatedBackendFetch,
} from "@/lib/server/cardyssey-api";

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

  const response =
    await authenticatedBackendFetch(
      `/api/v1/wishlist/${
        encodeURIComponent(id)
      }`,
      {
        method: "DELETE",
      }
    );

  return new Response(null, {
    status: response.status,
  });
}
