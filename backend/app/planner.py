"""Destination folders for plan items (REQ-CAT-8, REQ-ORG-1)."""
from __future__ import annotations

import re

UNSORTED = {"id": "_unsorted", "name": "Unsorted", "emoji": "🗂️"}
DUPLICATES = {"id": "_duplicates", "name": "Duplicates", "emoji": "🗑️"}

_BAD = re.compile(r'[\\:*?"<>|\x00-\x1f]')


def _clean(name: str) -> str:
    s = _BAD.sub("", name).replace("/", "-").strip().strip(".").strip()
    return re.sub(r"\s+", " ", s)[:80]


def safe_segment(name: str) -> str:
    return _clean(name) or "Untitled"


def safe_folder(name: str) -> str:
    """Category names may contain '/' to nest (date strategy); each part is sanitized, '..' parts dropped."""
    parts = [c for c in (_clean(p) for p in name.split("/")) if c]
    return "/".join(parts) or "Untitled"


def destination(source_rel: str, output_dir: str, kind: str, category: dict, split_media: bool) -> str:
    """Library-relative destination folder for a file."""
    # empty output_dir = put the category folders directly into the chosen folder
    out = safe_segment(output_dir) if output_dir and output_dir.strip() else ""
    root = [p for p in (source_rel.strip("/"), out) if p]
    if category["id"] == DUPLICATES["id"]:
        return "/".join(root + ["_Duplicates"])
    folder = safe_folder(category["name"])
    if split_media:
        return "/".join(root + ["Photos" if kind == "image" else "Videos", folder])
    return "/".join(root + [folder])
