export type AndroidReleaseInfo = {
  versionName: string;
  versionCode: number;
  buildNumber: number;
  commit: string;
  builtAt: string;
  file: string;
  sizeBytes: number;
  sha256: string;
};

export const ANDROID_RELEASE_METADATA_URL =
  "https://github.com/leonwilla/Cardyssey-Downloads/releases/latest/download/cardyssey-version.json";

export const ANDROID_APK_DOWNLOAD_URL =
  "https://github.com/leonwilla/Cardyssey-Downloads/releases/latest/download/cardyssey-latest.apk";

export function formatAndroidReleaseDate(
  value: string
) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat(
    "de-DE",
    {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Europe/Berlin",
    }
  ).format(date);
}

export async function getLatestAndroidRelease():
  Promise<AndroidReleaseInfo | null> {
  try {
    const response =
      await fetch(
        ANDROID_RELEASE_METADATA_URL,
        {
          next: {
            revalidate: 300,
          },
        }
      );

    if (!response.ok) {
      return null;
    }

    const data =
      await response.json() as
        Partial<AndroidReleaseInfo>;

    if (
      typeof data.versionName !== "string" ||
      typeof data.versionCode !== "number" ||
      typeof data.buildNumber !== "number" ||
      typeof data.commit !== "string" ||
      typeof data.builtAt !== "string"
    ) {
      return null;
    }

    return data as AndroidReleaseInfo;
  } catch {
    return null;
  }
}
