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
