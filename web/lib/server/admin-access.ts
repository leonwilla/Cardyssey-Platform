import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

export async function withAdminAccess(
  data: unknown,
  status: number
) {
  if (
    status < 200 ||
    status >= 300 ||
    data === null ||
    typeof data !== "object" ||
    Array.isArray(data)
  ) {
    return data;
  }

  const accessResponse =
    await authenticatedBackendFetch(
      "/api/v1/admin/access"
    );

  if (!accessResponse.ok) {
    return data;
  }

  const access =
    await readBackendJson(
      accessResponse
    );

  if (
    access === null ||
    typeof access !== "object" ||
    Array.isArray(access)
  ) {
    return data;
  }

  return {
    ...data,
    ...access,
  };
}
