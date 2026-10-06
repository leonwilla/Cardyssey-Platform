import {
  backendFetch,
} from "@/lib/server/cardyssey-api";

type Context = {
  params: Promise<{ fileName: string }>;
};

export async function GET(
  _request: Request,
  context: Context
) {
  const { fileName } =
    await context.params;

  const response =
    await backendFetch(
      `/api/v1/chat/group-images/${encodeURIComponent(fileName)}`
    );

  if (!response.ok) {
    return new Response(null, {
      status: response.status,
    });
  }

  const bytes =
    await response.arrayBuffer();

  return new Response(bytes, {
    status: 200,
    headers: {
      "Content-Type":
        response.headers.get("content-type") ??
        "image/jpeg",
      "Cache-Control":
        "public, max-age=3600",
    },
  });
}
