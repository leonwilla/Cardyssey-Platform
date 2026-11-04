import "server-only";
import { readFile } from "node:fs/promises";
import path from "node:path";
import type { AndroidReleaseInfo } from "@/lib/android-release";

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
