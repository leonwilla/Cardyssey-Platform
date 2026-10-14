"""Synchronize the verified current Cardyssey Android release into the web download path.

The Demo APK workflow publishes release assets to Cardyssey-Downloads. GitHub
Actions artifacts are ephemeral and need not exist after successful publishing.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "web/public/downloads/cardyssey-latest.apk"
SHA_FILE = ROOT / ".last-android-apk-sha"
REPO = "leonwilla/Cardyssey-Downloads"


def gh(*args):
    return subprocess.run(
        ["gh", *args], check=True, text=True, capture_output=True
    ).stdout


def main():
    release = json.loads(gh("api", f"repos/{REPO}/releases/latest"))
    tag = release["tag_name"]
    names = {a["name"] for a in release.get("assets", [])}
    if not {"cardyssey-latest.apk", "cardyssey-version.json"} <= names:
        raise RuntimeError(f"Release {tag} has no complete signed APK bundle")

    with tempfile.TemporaryDirectory(prefix="cardyssey-apk-") as directory:
        gh("release", "download", tag, "-R", REPO,
           "-p", "cardyssey-version.json", "-D", directory)
        metadata = json.loads((Path(directory) / "cardyssey-version.json").read_text())
        sha = metadata["sha256"].lower()
        commit = metadata["commit"]
        if not isinstance(commit, str) or len(commit) != 40 or len(sha) != 64:
            raise RuntimeError("Invalid release metadata")
        if metadata.get("file") != "cardyssey-latest.apk":
            raise RuntimeError("Unexpected APK filename")

        # Never skip an APK just because the SHA marker is up to date: check
        # the actual file against signed release metadata.
        if TARGET.is_file() and TARGET.stat().st_size == metadata["sizeBytes"]:
            if hashlib.sha256(TARGET.read_bytes()).hexdigest() == sha:
                if not SHA_FILE.is_file() or SHA_FILE.read_text().strip() != commit:
                    SHA_FILE.write_text(commit)
                print(f"APK current: {tag}, {commit[:8]}")
                return

        gh("release", "download", tag, "-R", REPO,
           "-p", "cardyssey-latest.apk", "-D", directory)
        apk = Path(directory) / "cardyssey-latest.apk"
        if apk.stat().st_size != metadata["sizeBytes"]:
            raise RuntimeError("APK size mismatch")
        if hashlib.sha256(apk.read_bytes()).hexdigest() != sha:
            raise RuntimeError("APK SHA256 mismatch")
        if not zipfile.is_zipfile(apk):
            raise RuntimeError("Downloaded artifact is not an APK")

        TARGET.parent.mkdir(parents=True, exist_ok=True)
        temporary = TARGET.with_suffix(".apk.tmp")
        try:
            with apk.open("rb") as source, temporary.open("wb") as dest:
                import shutil
                shutil.copyfileobj(source, dest)
            os.replace(temporary, TARGET)
        finally:
            temporary.unlink(missing_ok=True)
        SHA_FILE.write_text(commit)
        print(f"APK updated: {tag}, {commit[:8]}, {apk.stat().st_size} bytes")


if __name__ == "__main__":
    main()
