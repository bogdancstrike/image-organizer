"""Library scanning: discovery, path containment, folder browsing (spec: library-scanning)."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".3gp"}


class PathError(ValueError):
    """Requested path is outside the library or not a folder."""


@dataclass(frozen=True)
class MediaFile:
    id: str
    path: Path  # absolute
    rel_path: str  # relative to library root, posix style
    kind: str  # "image" | "video"
    size: int
    mtime: float

    @property
    def name(self) -> str:
        return self.path.name


def media_kind(name: str) -> str | None:
    ext = os.path.splitext(name)[1].lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    return None


def _inside(root: Path, p: Path) -> bool:
    return p == root or root in p.parents


def resolve_in_library(root: Path, rel: str | None) -> Path:
    """Resolve a user-supplied folder path inside the library root (REQ-SCAN-3)."""
    root = root.resolve()
    rel = (rel or "").strip().replace("\\", "/").lstrip("/")
    candidate = (root / rel).resolve()
    if not _inside(root, candidate):
        raise PathError("path escapes the library")
    if not candidate.is_dir():
        raise PathError("not a folder")
    return candidate


def file_id(rel_path: str) -> str:
    return hashlib.sha1(rel_path.encode("utf-8")).hexdigest()[:16]


def _skip_dir(name: str, output_dir_name: str) -> bool:
    return (
        name.startswith(".")
        or (bool(output_dir_name) and name == output_dir_name)
        or name in ("@eaDir", "_Duplicates")
    )


def scan(root: Path, source: Path, output_dir_name: str = "Organized", recursive: bool = True) -> list[MediaFile]:
    """Recursively list supported media under `source` (REQ-SCAN-1, REQ-SCAN-2)."""
    root = root.resolve()
    out: list[MediaFile] = []
    for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if not _skip_dir(d, output_dir_name)) if recursive else []
        for fn in filenames:
            if fn.startswith("."):
                continue
            kind = media_kind(fn)
            if kind is None:
                continue
            p = Path(dirpath) / fn
            try:
                real = p.resolve()
                if not _inside(root, real) or not real.is_file():
                    continue
                st = p.stat()
            except OSError:
                continue
            rel = p.relative_to(root).as_posix()
            out.append(MediaFile(file_id(rel), p, rel, kind, st.st_size, st.st_mtime))
    out.sort(key=lambda f: f.rel_path)
    return out


def list_folders(root: Path, rel: str | None, output_dir_name: str = "Organized") -> dict:
    """One level of folder browsing with direct media counts (REQ-SCAN-5)."""
    root = root.resolve()
    base = resolve_in_library(root, rel)
    folders = []
    media_here = 0
    try:
        entries = sorted(os.scandir(base), key=lambda e: e.name.lower())
    except OSError as exc:
        raise PathError(str(exc)) from exc
    for e in entries:
        if e.name.startswith("."):
            continue
        if e.is_dir(follow_symlinks=False):
            if _skip_dir(e.name, output_dir_name):
                continue
            count = 0
            has_children = False
            try:
                for sub in os.scandir(e.path):
                    if sub.name.startswith("."):
                        continue
                    if sub.is_dir(follow_symlinks=False):
                        has_children = True
                    elif media_kind(sub.name):
                        count += 1
            except OSError:
                pass
            folders.append({
                "name": e.name,
                "path": Path(e.path).relative_to(root).as_posix(),
                "media_count": count,
                "has_children": has_children,
            })
        elif media_kind(e.name):
            media_here += 1
    rel_path = "" if base == root else base.relative_to(root).as_posix()
    return {"path": rel_path, "name": base.name if rel_path else "Library", "media_count": media_here, "folders": folders}
