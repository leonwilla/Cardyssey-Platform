from pathlib import Path
import io
import json
import urllib.request
import urllib.error
import zipfile

ROOT = Path("/home/tv/cardshop")
ENV = ROOT / ".env"
TARGET = ROOT / "web/public/downloads/cardyssey-latest.apk"

token = None

for line in ENV.read_text().splitlines():
    if line.startswith("GITHUB_ANDROID_TOKEN="):
        token = line.split("=", 1)[1].strip()
        break

if not token:
    raise RuntimeError("GITHUB_ANDROID_TOKEN fehlt")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "Cardyssey-Tiny",
}

def github_json(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.load(response)

runs = github_json(
    "https://api.github.com/repos/"
    "GranBBX/Pokemonkarten-APP/actions/workflows/"
    "android-demo-apk.yml/runs"
    "?branch=main&status=success&per_page=1"
)

if not runs.get("workflow_runs"):
    raise RuntimeError("Kein erfolgreicher APK-Workflow gefunden")

run = runs["workflow_runs"][0]
run_id = run["id"]

print("Workflow:", run_id)
print("Commit:", run["head_sha"][:8])

sha = run["head_sha"]
sha_file = ROOT / ".last-android-apk-sha"

if (
    TARGET.exists()
    and sha_file.exists()
    and sha_file.read_text().strip() == sha
):
    print("APK bereits aktuell.")
    raise SystemExit(0)

artifacts = github_json(
    "https://api.github.com/repos/"
    f"GranBBX/Pokemonkarten-APP/actions/runs/{run_id}/artifacts"
)

artifact = next(
    (
        a for a in artifacts.get("artifacts", [])
        if a["name"] == "cardyssey-android-latest"
    ),
    None,
)

if not artifact:
    raise RuntimeError("Artifact cardyssey-android-latest nicht gefunden")

archive_url = artifact["archive_download_url"]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = urllib.request.build_opener(NoRedirect)

req = urllib.request.Request(
    archive_url,
    headers=headers,
)

try:
    opener.open(req)
    raise RuntimeError("GitHub lieferte keinen Download-Redirect")
except urllib.error.HTTPError as error:
    if error.code not in (301, 302, 303, 307, 308):
        raise

    storage_url = error.headers.get("Location")

if not storage_url:
    raise RuntimeError("GitHub Download-Redirect enthält keine Location")

# Wichtig: temporären Storage-Link OHNE GitHub Token abrufen.
req = urllib.request.Request(
    storage_url,
    headers={"User-Agent": "Cardyssey-Tiny"},
)

with urllib.request.urlopen(req) as response:
    zip_data = response.read()

with zipfile.ZipFile(io.BytesIO(zip_data)) as archive:
    apk = next(
        (
            name for name in archive.namelist()
            if name.endswith(".apk")
        ),
        None,
    )

    if not apk:
        raise RuntimeError("Keine APK im Artifact gefunden")

    apk_data = archive.read(apk)

tmp = TARGET.with_suffix(".apk.tmp")
tmp.write_bytes(apk_data)
tmp.replace(TARGET)
sha_file.write_text(sha)

print("APK aktualisiert:")
print(TARGET)
print(f"Größe: {TARGET.stat().st_size / 1024 / 1024:.1f} MB")
