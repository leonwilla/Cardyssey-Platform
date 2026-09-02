import type {
  CreateMarketplaceOfferRequest,
} from "@/lib/generated/cardyssey/src";

import {
  generatedApiError,
  offersApi,
} from "@/lib/server/generated-cardyssey";

export async function POST(
  request: Request
) {
  try {
    const body =
      (
        await request.json()
      ) as CreateMarketplaceOfferRequest;

    const offer =
      await offersApi()
        .createOffer({
          createMarketplaceOfferRequest:
            body,
        });

    return Response.json(
      offer,
      {
        status: 201,
      }
    );

  } catch (error) {
    return generatedApiError(
      error
    );
  }
}
