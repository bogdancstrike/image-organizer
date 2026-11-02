"""Library scanning: discovery, path containment, folder browsing (spec: library-scanning)."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

RAW_EXT = {".cr2", ".cr3", ".nef", ".nrw", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw"}
IMAGE_EXT = {
    ".jpg", ".jpeg", ".jpe", ".jfif", ".png", ".apng", ".webp", ".gif", ".bmp", ".dib", ".tif", ".tiff",
    ".heic", ".heif", ".hif", ".avif", ".jxl", ".jp2", ".j2k", ".jpf", ".psd", ".tga", ".ppm", ".pgm", ".pbm",
    ".ico", ".qoi",
} | RAW_EXT
SIDECAR_EXT = {".xmp", ".aae", ".thm", ".pp3", ".dop"}


def is_raw(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in RAW_EXT
VIDEO_EXT = {
    ".mp4", ".m4v", ".mov", ".qt", ".webm", ".mkv", ".avi", ".3gp", ".3g2", ".mts", ".m2ts", ".ts", ".wmv",
    ".asf", ".flv", ".f4v", ".mpg", ".mpeg", ".m2v", ".vob", ".ogv", ".mxf", ".divx", ".insv",
}


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
    sidecars: tuple[str, ...] = ()  # rel paths that travel with this file (RAW of a RAW+JPEG pair, .xmp, …)

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
        or name in ("@eaDir", "_Duplicates", "_Rejects")
    )


def _stem(name: str) -> str:
    """'IMG_1.CR2.xmp' -> 'img_1', 'IMG_1.jpg' -> 'img_1'."""
    base = name.lower()
    for _ in range(2):
        b, ext = os.path.splitext(base)
        if ext in IMAGE_EXT or ext in VIDEO_EXT or ext in SIDECAR_EXT:
            base = b
    return base


def _pair(files: list[MediaFile], sidecar_paths: list[str]) -> list[MediaFile]:
    """Within one folder: a RAW with a same-named JPEG/HEIC rides along with it; sidecar files attach to their photo."""
    groups: dict[str, list[MediaFile]] = {}
    for f in files:
        groups.setdefault(_stem(f.name), []).append(f)
    side_by_stem: dict[str, list[str]] = {}
    for sp in sidecar_paths:
        side_by_stem.setdefault(_stem(Path(sp).name), []).append(sp)
    out: list[MediaFile] = []
    for stem, members in groups.items():
        raws = [m for m in members if is_raw(m.name)]
        others = [m for m in members if not is_raw(m.name)]
        if raws and others:
            primary = sorted(others, key=lambda m: (m.kind != "image", m.name))[0]
            rest = [m for m in others if m is not primary]
            extra = tuple(m.rel_path for m in raws) + tuple(side_by_stem.pop(stem, []))
            out.append(MediaFile(primary.id, primary.path, primary.rel_path, primary.kind, primary.size, primary.mtime, extra))
            out.extend(rest)
        else:
            first, *rest = members
            extra = tuple(side_by_stem.pop(stem, []))
            out.append(MediaFile(first.id, first.path, first.rel_path, first.kind, first.size, first.mtime, extra) if extra else first)
            out.extend(rest)
    return out


def scan(
    root: Path, source: Path, output_dir_name: str = "Organized", recursive: bool = True, pair_sidecars: bool = True
) -> list[MediaFile]:
    """Recursively list supported media under `source` (REQ-SCAN-1, REQ-SCAN-2)."""
    root = root.resolve()
    out: list[MediaFile] = []
    for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if not _skip_dir(d, output_dir_name)) if recursive else []
        here: list[MediaFile] = []
        sidecars: list[str] = []
        for fn in filenames:
            if fn.startswith("."):
                continue
            kind = media_kind(fn)
            if kind is None:
                if pair_sidecars and os.path.splitext(fn)[1].lower() in SIDECAR_EXT:
                    sidecars.append((Path(dirpath) / fn).relative_to(root).as_posix())
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
            here.append(MediaFile(file_id(rel), p, rel, kind, st.st_size, st.st_mtime))
        out.extend(_pair(here, sidecars) if pair_sidecars else here)
    out.sort(key=lambda f: f.rel_path)
    return out


def list_folders(root: Path, rel: str | None, output_dir_name: str = "Organized") -> dict:
    """One level of folder browsing with direct media counts (REQ-SCAN-5)."""
    root = root.resolve()
    base = resolve_in_library(root, rel)
    folders = []
    media_here = 0
    samples: list[str] = []
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
            if len(samples) < 8 and media_kind(e.name) == "image":
                samples.append(Path(e.path).relative_to(root).as_posix())
    rel_path = "" if base == root else base.relative_to(root).as_posix()
    return {"path": rel_path, "name": base.name if rel_path else "Library", "media_count": media_here, "folders": folders,
            "samples": samples}


# Well-known folders (incl. common localized names) shown as "Places" in the folder picker
PLACES = [
    ("pictures", ("Pictures", "Imagini", "Bilder", "Images", "Imágenes", "Photos")),
    ("downloads", ("Downloads", "Descărcări", "Téléchargements", "Descargas")),
    ("desktop", ("Desktop", "Birou", "Schreibtisch", "Bureau", "Escritorio")),
    ("documents", ("Documents", "Documente", "Dokumente", "Documentos")),
    ("videos", ("Videos", "Video", "Videoclipuri", "Vidéos", "Vídeos")),
    ("dcim", ("DCIM",)),
]


def list_places(root: Path) -> list[dict]:
    root = root.resolve()
    out = []
    for kind, names in PLACES:
        for n in names:
            p = root / n
            if p.is_dir() and not p.is_symlink():
                out.append({"kind": kind, "name": n, "path": n})
                break
    return out
