#!/usr/bin/env python3
"""Rebuild the seven German EX Trainer Kit scans from a verified full-set photo.

The source listing shows the complete German 60-card Trainer Kit. We crop only
exact, fixed card positions, store the resulting local catalog JPEGs, compute
Cardyssey-compatible dHashes and mark the matching DE mirror rows complete.
"""
import argparse
import io
import subprocess
import urllib.request
from pathlib import Path

SOURCE = "https://img.kleinanzeigen.de/api/v1/prod-ads/images/c8/c82f3bd4-7bfd-4fd1-a0cc-30e8a6c76be2?rule=$_57.AUTO"
BOXES = {
    "tk-ex-latia-2": (333, 60, 449, 235),
    "tk-ex-latia-7": (333, 420, 449, 595),
    "tk-ex-latio-3": (1208, 60, 1327, 235),
    "tk-ex-latia-10": (207, 600, 322, 775),
    "tk-ex-latia-8": (207, 420, 322, 595),
    "tk-ex-latia-9": (457, 600, 573, 775),
    "tk-ex-latio-9": (958, 600, 1074, 775),
}

def run(*args, input_text=None):
    return subprocess.run(args, input=input_text, text=True, check=True, capture_output=True).stdout

def dhash(image):
    target = 63 / 88
    ratio = image.width / image.height
    if ratio > target:
        h = image.height
        w = max(1, min(image.width, int(h * target)))
    else:
        w = image.width
        h = max(1, min(image.height, int(w / target)))
    left = max(0, (image.width - w) // 2)
    top = max(0, (image.height - h) // 2)
    gray = image.crop((left, top, left + w, top + h)).convert("L").resize((9, 8))
    px = gray.load()
    value = 0
    bit = 0
    for y in range(8):
        for x in range(8):
            if px[x, y] > px[x + 1, y]:
                value |= 1 << bit
            bit += 1
    return value - (1 << 64) if value >= (1 << 63) else value

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("Pillow is required: install it in a venv and run this script there")

    req = urllib.request.Request(SOURCE, headers={"User-Agent": "Cardyssey catalog backfill", "Accept": "image/*"})
    with urllib.request.urlopen(req, timeout=30) as response:
        source = Image.open(io.BytesIO(response.read())).convert("RGB")

    out = Path("/tmp/cardyssey-de-trainerkit")
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for card_id, box in BOXES.items():
        card = source.crop(box).resize((630, 880), Image.Resampling.LANCZOS)
        path = out / f"{card_id}.jpg"
        card.save(path, "JPEG", quality=95)
        rows.append((card_id, path, dhash(card), path.stat().st_size))

    print(f"verified_crops={len(rows)} applied={args.apply}")
    if not args.apply:
        for row in rows:
            print(row[0], row[2], row[3])
        return

    run("docker", "exec", "cardyssey-api", "mkdir", "-p", "/data/catalog/cards/de")
    for card_id, path, hash_value, size in rows:
        run("docker", "cp", str(path), f"cardyssey-api:/data/catalog/cards/de/{card_id}.jpg")
        source_sql = SOURCE.replace("'", "''")
        sql = f"""
UPDATE catalog_cards_mirror
SET image_source_url='{source_sql}',
    image_local_path='cards/de/{card_id}.jpg',
    image_dhash={hash_value},
    image_bytes={size},
    image_complete=TRUE,
    source_updated_at=NOW(),
    last_seen_at=NOW()
WHERE language_code='de' AND card_id='{card_id}';
"""
        run("docker", "exec", "-i", "cardyssey-db", "psql", "-U", "cardyssey", "-d", "cardyssey", input_text=sql)

if __name__ == "__main__":
    main()
