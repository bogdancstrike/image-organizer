"""Decoding, thumbnails, hashes, EXIF and video frames (spec: media-analysis)."""
from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import imagehash
from PIL import Image, ImageOps

try:  # HEIC/HEIF/AVIF support
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover - optional
    pass
try:  # JPEG XL support
    import pillow_jxl  # noqa: F401
except Exception:  # pragma: no cover - optional
    pass

Image.MAX_IMAGE_PIXELS = 200_000_000

THUMB_SIZE = 160
EMBED_SIZE = 448
SCREENSHOT_RE = re.compile(r"screenshot|screen ?shot|scr_|captura|bildschirmfoto", re.I)

_EXIF_IFD = 0x8769
_DATETIME_ORIGINAL = 36867
_DATETIME = 306
_MAKE, _MODEL = 271, 272


class MediaError(Exception):
    pass


@dataclass
class Analysis:
    """Cacheable metadata (everything except embeddings and frames)."""

    width: int
    height: int
    captured_at: float
    sha256: str
    phash: str | None
    is_screenshot: bool
    duration: float | None = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> "Analysis":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class Decoded:
    analysis: Analysis
    frames: list[Image.Image] = field(default_factory=list)  # RGB, ≤ EMBED_SIZE, for embedding
    thumb: bytes = b""


FULL_HASH_LIMIT = 64 << 20  # files above 64 MB get a sampled hash
SAMPLE = 4 << 20


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    """SHA-256 of the content. Large files (typically videos) hash size + head + middle + tail,
    which is plenty to recognise byte-identical copies without reading gigabytes."""
    size = path.stat().st_size
    h = hashlib.sha256()
    if size > FULL_HASH_LIMIT:
        h.update(f"sampled:{size}:".encode())
        with open(path, "rb") as f:
            for off in (0, size // 2 - SAMPLE // 2, size - SAMPLE):
                f.seek(max(0, off))
                h.update(f.read(SAMPLE))
        return h.hexdigest()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _parse_exif_dt(value) -> float | None:
    if not value:
        return None
    s = str(value).strip().replace("\x00", "")
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).timestamp()
        except ValueError:
            continue
    return None


def make_thumb(img: Image.Image, size: int = THUMB_SIZE) -> bytes:
    t = img.copy()
    t.thumbnail((size, size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    t.save(buf, "WEBP", quality=78, method=4)
    return buf.getvalue()


def is_screenshot_like(name: str, fmt: str | None, has_camera: bool, width: int, height: int) -> bool:
    """REQ-ANL-5 screenshot signal."""
    if SCREENSHOT_RE.search(name):
        return True
    if (fmt or "").upper() == "PNG" and not has_camera and width > 0 and height / width >= 1.7:
        return True
    return False


RAW_EXT = {".cr2", ".cr3", ".nef", ".nrw", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw"}


def open_any(path: Path) -> Image.Image:
    """Image.open, plus camera RAW via the embedded JPEG preview (fast) or a half-size demosaic."""
    if path.suffix.lower() not in RAW_EXT:
        return Image.open(path)
    import rawpy

    with rawpy.imread(str(path)) as raw:
        try:
            th = raw.extract_thumb()
            if th.format == rawpy.ThumbFormat.JPEG:
                return Image.open(io.BytesIO(th.data))
            return Image.fromarray(th.data)
        except (rawpy.LibRawNoThumbnailError, rawpy.LibRawUnsupportedThumbnailError):
            return Image.fromarray(raw.postprocess(half_size=True, use_camera_wb=True))


def load_for_quality(path: Path, size: int = 2048) -> Image.Image:
    with open_any(path) as im:
        if im.format == "JPEG":
            im.draft("RGB", (size, size))
        im = ImageOps.exif_transpose(im)
        return im.convert("RGB")


def decode_image(path: Path, mtime: float) -> Decoded:
    try:
        with open_any(path) as im:
            fmt = im.format
            exif = im.getexif()
            orig_w, orig_h = im.size
            if exif and exif.get(0x0112) in (5, 6, 7, 8):  # rotated 90/270 degrees
                orig_w, orig_h = orig_h, orig_w
            if fmt == "JPEG":
                im.draft("RGB", (EMBED_SIZE * 2, EMBED_SIZE * 2))  # fast DCT downscale
            im = ImageOps.exif_transpose(im)
            rgb = im.convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise MediaError(f"cannot decode image: {exc}") from exc

    captured = None
    has_camera = False
    if exif:
        try:
            captured = _parse_exif_dt(exif.get_ifd(_EXIF_IFD).get(_DATETIME_ORIGINAL)) or _parse_exif_dt(exif.get(_DATETIME))
        except Exception:  # noqa: BLE001
            captured = None
        has_camera = bool(exif.get(_MAKE) or exif.get(_MODEL))

    small = rgb.copy()
    small.thumbnail((EMBED_SIZE, EMBED_SIZE), Image.Resampling.BILINEAR)
    a = Analysis(
        width=orig_w,
        height=orig_h,
        captured_at=captured or mtime,
        sha256=sha256_file(path),
        phash=str(imagehash.phash(small)),
        is_screenshot=is_screenshot_like(path.name, fmt, has_camera, orig_w, orig_h),
    )
    return Decoded(a, [small], make_thumb(small))


def _ffprobe(path: Path) -> dict:
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=30, check=True)
        return json.loads(r.stdout or b"{}")
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError) as exc:
        raise MediaError(f"ffprobe failed: {exc}") from exc


VIDEO_FRAME_SIZE = 336  # CLIP looks at 224 px; small frames keep ffmpeg fast


def _frame_at(path: Path, t: float) -> Image.Image | None:
    """One frame near t: fast input seek + keyframe-only decode, no audio/subtitles, small output."""
    cmd = [
        "ffmpeg", "-v", "error", "-nostdin", "-threads", "1", "-skip_frame", "nokey",
        "-ss", f"{max(t, 0):.3f}", "-i", str(path), "-map", "0:v:0", "-an", "-sn", "-dn", "-frames:v", "1",
        "-vf", f"scale='min({VIDEO_FRAME_SIZE},iw)':-2", "-f", "image2pipe", "-vcodec", "bmp", "-",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=30)
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    if r.returncode != 0 or not r.stdout:
        return None
    try:
        return Image.open(io.BytesIO(r.stdout)).convert("RGB")
    except Exception:  # noqa: BLE001
        return None


def _iso_to_ts(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def decode_video(path: Path, mtime: float) -> Decoded:
    info = _ffprobe(path)
    vstreams = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    if not vstreams:
        raise MediaError("no video stream")
    vs = vstreams[0]
    fmt = info.get("format", {})
    try:
        duration = float(fmt.get("duration") or vs.get("duration") or 0)
    except ValueError:
        duration = 0.0
    width, height = int(vs.get("width") or 0), int(vs.get("height") or 0)
    rotate = str((vs.get("tags") or {}).get("rotate", ""))
    for sd in vs.get("side_data_list", []) or []:
        if "rotation" in sd:
            rotate = str(sd["rotation"])
    if rotate.lstrip("-") in {"90", "270"}:
        width, height = height, width
    created = _iso_to_ts((fmt.get("tags") or {}).get("creation_time")) or _iso_to_ts((vs.get("tags") or {}).get("creation_time"))

    # fewer frames for short clips: 1 (<4 s), 2 (<15 s), 3 otherwise
    if duration <= 0:
        points = [0.0]
    elif duration < 4:
        points = [0.5]
    elif duration < 15:
        points = [0.3, 0.7]
    else:
        points = [0.2, 0.5, 0.8]
    frames = [f for f in (_frame_at(path, duration * p) for p in points) if f is not None]
    if not frames:
        f0 = _frame_at(path, 0)
        if f0 is None:
            raise MediaError("cannot extract frames")
        frames = [f0]
    middle = frames[len(frames) // 2]
    thumb_src = frames[min(1, len(frames) - 1)] if len(frames) > 1 else frames[0]
    a = Analysis(
        width=width or middle.width,
        height=height or middle.height,
        captured_at=created or mtime,
        sha256=sha256_file(path),
        phash=str(imagehash.phash(middle)),
        is_screenshot=False,
        duration=duration,
    )
    return Decoded(a, frames, make_thumb(thumb_src))


def decode(path: Path, kind: str, mtime: float) -> Decoded:
    return decode_image(path, mtime) if kind == "image" else decode_video(path, mtime)
