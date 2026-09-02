import {
  generatedApiError,
  offersApi,
} from "@/lib/server/generated-cardyssey";

export async function GET() {
  try {
    return Response.json(
      await offersApi()
        .getIncomingOffers()
    );
  } catch (error) {
    return generatedApiError(
      error
    );
  }
}
