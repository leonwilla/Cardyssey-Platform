import { backendFetch, readBackendJson, setAuthCookies } from "@/lib/server/cardyssey-api";

export async function POST(request: Request) {
  const body = await request.text();
  const response = await backendFetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  const data = await readBackendJson(response);
  if (!response.ok) return Response.json(data, { status: response.status });

  await setAuthCookies(data);
  return Response.json({ user: data.user });
}
