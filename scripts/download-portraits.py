#!/usr/bin/env python3
"""Download openly licensed portrait / fashion / selfie photos from Wikimedia Commons into the sample library.

Usage: python3 scripts/download-portraits.py [DEST] [TOTAL] [MIX]
MIX: "portraits" (default: portraits, outfits, selfies) or "boudoir" (adult boudoir, lingerie & glamour photography).
Default: ./sample-library/Portraits, 200 files. Only uses the standard library.
Each photo keeps its Commons file name; licenses are listed on its Commons page.
"""
from __future__ import annotations

import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "AutoImageOrganizer/0.1 (https://github.com/bogdancstrike/image-organizer; sample data script)"
API = "https://commons.wikimedia.org/w/api.php"
# category -> share of the total
MIXES: dict[str, dict[str, float]] = {}
MIX = {
    "Street_fashion": 0.2,
    "Fashion_photography": 0.2,
    "Women_wearing_dresses": 0.15,
    "Portrait_photographs_of_women": 0.15,
    "Portrait_photographs_of_men": 0.15,
    "Selfies": 0.15,
}
MIXES["portraits"] = MIX
MIXES["boudoir"] = {  # adult, professional boudoir / lingerie / glamour photography
    "Boudoir_photography": 0.56,
    "Stockings": 0.12,
    "Corsets": 0.11,
    "Lingerie": 0.11,
    "Glamour_models": 0.06,
    "Garter_belts": 0.02,
    "Victoria's_Secret_Fashion_Show": 0.02,
}


def get_json(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def thumbs(category: str, width: int = 900) -> list[tuple[str, str]]:
    out, cont = [], {}
    while True:
        d = get_json({
            "action": "query", "generator": "categorymembers", "gcmtitle": f"Category:{category.replace('_', ' ')}",
            "gcmtype": "file", "gcmlimit": 200, "prop": "imageinfo", "iiprop": "url|mime",
            "iiurlwidth": width, **cont,
        })
        for page in d.get("query", {}).get("pages", {}).values():
            info = (page.get("imageinfo") or [{}])[0]
            if info.get("mime") == "image/jpeg" and info.get("thumburl"):
                out.append((page["title"].split(":", 1)[1], info["thumburl"]))
        if "continue" not in d or len(out) >= 600:
            return out
        cont = d["continue"]


def main() -> None:
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else "sample-library/Portraits")
    total = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    mix = MIXES.get(sys.argv[3] if len(sys.argv) > 3 else "portraits", MIX)
    dest.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    done = 0
    for cat, share in mix.items():
        want = round(total * share)
        items = thumbs(cat)
        rng.shuffle(items)
        got = 0
        for name, url in items:
            if got >= want:
                break
            safe = "".join(ch if ch.isalnum() or ch in " ._-()" else "_" for ch in name)[:120]
            target = dest / safe
            if target.exists() and target.stat().st_size > 0:
                got += 1
                continue
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    target.write_bytes(r.read())
                got += 1
            except Exception as exc:  # noqa: BLE001 - skip and keep going
                print(f"  skip {name}: {exc}", file=sys.stderr)
            time.sleep(0.15)  # be polite to Wikimedia
        done += got
        print(f"{cat}: {got}/{want}")
    print(f"Done: {done} files in {dest}")


if __name__ == "__main__":
    main()
