import {
  getLatestAndroidRelease,
} from "@/lib/android-release";

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
          "public, max-age=60, s-maxage=300",
      },
    }
  );
}
