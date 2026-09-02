import {
  Configuration,
  OffersApi,
} from "@/lib/generated/cardyssey/src";

import type {
  FetchAPI,
} from "@/lib/generated/cardyssey/src/runtime";

import {
  authenticatedBackendFetch,
  readBackendJson,
} from "@/lib/server/cardyssey-api";

const generatedFetch: FetchAPI =
  async (
    input,
    init
  ) => {
    const raw =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

    const url =
      new URL(
        raw,
        "http://cardyssey.internal"
      );

    return authenticatedBackendFetch(
      `${url.pathname}${url.search}`,
      init
    );
  };

function configuration() {
  return new Configuration({
    basePath:
      "http://cardyssey.internal",

    fetchApi:
      generatedFetch,
  });
}

export function offersApi() {
  return new OffersApi(
    configuration()
  );
}

export async function generatedApiError(
  error: unknown
) {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error
  ) {
    const response =
      (
        error as {
          response?: Response;
        }
      ).response;

    if (response) {
      return Response.json(
        await readBackendJson(
          response
        ),
        {
          status:
            response.status,
        }
      );
    }
  }

  console.error(
    "Generated Cardyssey API error:",
    error
  );

  return Response.json(
    {
      error:
        "backend_request_failed",
    },
    {
      status: 502,
    }
  );
}
