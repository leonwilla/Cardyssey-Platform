import { readFile } from "node:fs/promises";
import path from "node:path";

export type AndroidReleaseInfo = {
  versionName: string;
  versionCode: number;
  buildNumber: number;
  commit: string;
  builtAt: string;
  file: string;
  sizeBytes: number;
  sha256: string;
  signingCertificateSha256?: string;
};

export const ANDROID_APK_DOWNLOAD_URL =
  "/api/private/apk";

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
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "Europe/Berlin",
    }
  )
    .format(date)
    .replace(", ", " · ") + " Uhr";
}

/** Use the same private, signed release metadata as the native Android updater.
 * Do not use the legacy GitHub latest release (which may be months behind). */
export async function getLatestAndroidRelease():
  Promise<AndroidReleaseInfo | null> {
  try {
    const directory = process.env.CARDYSSEY_PRIVATE_RELEASE_DIR ||
      "/home/tv/cardshop/web/private-downloads";
    const contents = await readFile(path.join(directory, "cardyssey-version.json"), "utf8");
    const data = JSON.parse(contents) as Partial<AndroidReleaseInfo>;
    if (
      typeof data.versionName !== "string" ||
      typeof data.versionCode !== "number" || data.versionCode <= 0 ||
      typeof data.buildNumber !== "number" ||
      typeof data.commit !== "string" || !/^[a-f0-9]{40}$/i.test(data.commit) ||
      typeof data.builtAt !== "string" ||
      typeof data.sha256 !== "string" || !/^[a-f0-9]{64}$/i.test(data.sha256) ||
      data.file !== "cardyssey-latest.apk"
    ) return null;
    return data as AndroidReleaseInfo;
  } catch {
    return null;
  }
}
