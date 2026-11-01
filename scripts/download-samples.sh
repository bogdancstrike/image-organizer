#!/usr/bin/env bash
# Fill ./sample-library with free sample photos (picsum.photos, Unsplash license),
# plus a few duplicates, a fake screenshot and short videos, to try the app.
set -euo pipefail
DEST="${1:-./sample-library}"
COUNT="${COUNT:-80}"
mkdir -p "$DEST/Downloads"
cd "$DEST/Downloads"

echo "Downloading $COUNT sample photos into $DEST/Downloads …"
for i in $(seq 1 "$COUNT"); do
  f="IMG_$(printf '%04d' "$i").jpg"
  [ -s "$f" ] || curl -fsSL "https://picsum.photos/id/$((i * 7 % 1000))/900/700" -o "$f" || rm -f "$f"
done

# duplicates: an exact copy and a resized copy
cp IMG_0001.jpg "IMG_0001 (1).jpg" 2>/dev/null || true
if command -v ffmpeg >/dev/null; then
  ffmpeg -v error -y -i IMG_0002.jpg -vf scale=450:-1 IMG_0002_small.jpg || true
  # short clips made from photos
  for i in 3 4 5; do
    ffmpeg -v error -y -loop 1 -i "IMG_000$i.jpg" -t 2 -vf "scale=640:-2,zoompan=z='min(zoom+0.0015,1.2)':d=60" \
      -pix_fmt yuv420p "clip_$i.mp4" || true
  done
  # a phone-shaped PNG (screenshot heuristic)
  ffmpeg -v error -y -f lavfi -i "color=c=white:s=1080x2340" -frames:v 1 "Screenshot_2026-05-01-10-00-00.png" || true
fi
echo "Done: $(ls | wc -l) files in $DEST/Downloads"
