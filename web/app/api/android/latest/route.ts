import {
  getLatestAndroidRelease,
} from "@/lib/server/android-release-server";

export async function GET() {
  const release =
    await getLatestAndroidRelease();

  if (!release) {
    return Response.json(
      {
        error:
          "android_release_unavailable",
      },
      {
        status: 503,
      }
    );
  }

  return Response.json(
    release,
    {
      headers: {
        "Cache-Control":
          "private, no-store",
      },
    }
  );
}
