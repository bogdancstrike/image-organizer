"""Photo quality signals for culling: sharpness, exposure, faces, blink, smile (spec: quality-culling).

Raw scores are cached; thresholds are applied at classification time, so users can tune them
without re-analysing.

- Sharpness: variance of the Laplacian on a 512 px grayscale. Measured on detected faces when there are
  any (shallow depth of field is intentional in portraits), otherwise on the sharpest of 4x4 tiles.
  Normalized to 0..1 as log10(var) / 4 (var 100 -> 0.5, var 10_000 -> 1.0).
- Exposure: mean luminance and the share of crushed blacks / blown highlights.
- Faces: MediaPipe Face Landmarker blendshapes, per face eyeBlink{Left,Right} and mouthSmile{Left,Right}.
"""
from __future__ import annotations

import logging
import math
import os
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

log = logging.getLogger(__name__)

FACE_MODEL_ENV = "FACE_MODEL"
ANALYSIS_SIZE = 1024
DETECT_SIZE = 2048  # faces are searched on this resolution (tiled)
MIN_FACE_AREA = 0.0006  # ignore tiny background faces (eyes unreadable)


@dataclass
class Face:
    blink: float  # 0..1, mean of both eyes
    smile: float  # 0..1
    area: float  # share of the image area
    box: tuple[float, float, float, float]  # x0, y0, x1, y1 normalized


@dataclass
class Quality:
    sharpness: float  # 0..1
    brightness: float  # 0..1 mean luminance
    dark_clip: float  # share of pixels < 3%
    bright_clip: float  # share of pixels > 97%
    faces: list[Face] = field(default_factory=list)
    faces_checked: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Quality":
        faces = [Face(**{**f, "box": tuple(f["box"])}) for f in d.get("faces", [])]
        return cls(d["sharpness"], d["brightness"], d["dark_clip"], d["bright_clip"], faces, d.get("faces_checked", False))


def _lap_var(gray: np.ndarray) -> float:
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    g = gray.astype(np.float32)
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(lap.var())


def _norm_sharp(var: float) -> float:
    return max(0.0, min(1.0, math.log10(max(var, 1.0)) / 4.0))


def sharpness(gray512: np.ndarray, faces: list[Face]) -> float:
    h, w = gray512.shape
    if faces:
        best = 0.0
        for f in faces:
            x0, y0, x1, y1 = f.box
            # focus on the eye region: upper 60% of the face box
            crop = gray512[int(y0 * h) : int((y0 + (y1 - y0) * 0.6) * h) + 1, int(x0 * w) : int(x1 * w) + 1]
            if crop.size >= 400:
                best = max(best, _lap_var(crop))
        if best > 0:
            return _norm_sharp(best)
    best = 0.0
    for i in range(4):
        for j in range(4):
            tile = gray512[i * h // 4 : (i + 1) * h // 4, j * w // 4 : (j + 1) * w // 4]
            if tile.size > 100:
                best = max(best, _lap_var(tile))
    return _norm_sharp(best)


class FaceAnalyzer:
    """Thread-local MediaPipe Face Landmarker instances (they are not thread-safe)."""

    def __init__(self, model_path: str | None):
        self.model_path = model_path if model_path and Path(model_path).exists() else None
        self._local = threading.local()
        if not self.model_path:
            log.warning("face model not found (%s): eyes/smile checks disabled", model_path)

    @property
    def available(self) -> bool:
        return self.model_path is not None

    def _get(self):
        lm = getattr(self._local, "lm", None)
        if lm is None:
            from mediapipe.tasks.python import BaseOptions, vision

            opts = vision.FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=self.model_path),
                output_face_blendshapes=True,
                num_faces=8,
                min_face_detection_confidence=0.5,
                running_mode=vision.RunningMode.IMAGE,
            )
            lm = vision.FaceLandmarker.create_from_options(opts)
            self._local.lm = lm
        return lm

    def _detect_one(self, rgb: np.ndarray) -> list[tuple[tuple[float, float, float, float], float, float]]:
        import mediapipe as mp

        res = self._get().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        out = []
        for lms, bs in zip(res.face_landmarks, res.face_blendshapes):
            sc = {c.category_name: c.score for c in bs}
            xs = [p.x for p in lms]
            ys = [p.y for p in lms]
            out.append((
                (min(xs), min(ys), max(xs), max(ys)),
                (sc.get("eyeBlinkLeft", 0) + sc.get("eyeBlinkRight", 0)) / 2,
                (sc.get("mouthSmileLeft", 0) + sc.get("mouthSmileRight", 0)) / 2,
            ))
        return out

    def detect(self, rgb: np.ndarray) -> list[Face]:
        """MediaPipe's detector is short-range (selfie-sized faces). To find faces in full-body and
        group shots we also run it on overlapping 2x2 and 3x3 tiles and merge the results."""
        H, W = rgb.shape[:2]
        found: list[Face] = []

        def add(box, blink, smile):
            x0, y0, x1, y1 = (max(0.0, box[0]), max(0.0, box[1]), min(1.0, box[2]), min(1.0, box[3]))
            area = (x1 - x0) * (y1 - y0)
            if area < MIN_FACE_AREA:
                return
            for i, f in enumerate(found):
                if _iou(f.box, (x0, y0, x1, y1)) > 0.3:
                    if area > f.area:  # keep the better-resolved detection
                        found[i] = Face(round(blink, 3), round(smile, 3), round(area, 5), (x0, y0, x1, y1))
                    return
            found.append(Face(round(blink, 3), round(smile, 3), round(area, 5), (x0, y0, x1, y1)))

        full = Image.fromarray(rgb)
        small = full.copy()
        small.thumbnail((ANALYSIS_SIZE, ANALYSIS_SIZE))
        for box, blink, smile in self._detect_one(np.asarray(small)):
            add(box, blink, smile)
        for n in (2, 3):
            tw, th = W / n, H / n
            ox, oy = tw * 0.25, th * 0.25  # 25% overlap
            for i in range(n):
                for j in range(n):
                    x0, y0 = max(0, int(j * tw - ox)), max(0, int(i * th - oy))
                    x1, y1 = min(W, int((j + 1) * tw + ox)), min(H, int((i + 1) * th + oy))
                    tile = full.crop((x0, y0, x1, y1))
                    tile.thumbnail((ANALYSIS_SIZE, ANALYSIS_SIZE))
                    for (bx0, by0, bx1, by1), blink, smile in self._detect_one(np.asarray(tile)):
                        cw, ch = x1 - x0, y1 - y0
                        add(((x0 + bx0 * cw) / W, (y0 + by0 * ch) / H, (x0 + bx1 * cw) / W, (y0 + by1 * ch) / H), blink, smile)
        for f in found:
            f.box = tuple(round(v, 4) for v in f.box)
        return found


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


_face_analyzer: FaceAnalyzer | None = None
_fa_lock = threading.Lock()


def get_face_analyzer() -> FaceAnalyzer:
    global _face_analyzer
    with _fa_lock:
        if _face_analyzer is None:
            _face_analyzer = FaceAnalyzer(os.environ.get(FACE_MODEL_ENV, "/models/face_landmarker.task"))
        return _face_analyzer


def analyze_image(img: Image.Image, faces: FaceAnalyzer | None) -> Quality:
    """img: RGB, any size (it is reduced here)."""
    big = img.convert("RGB")
    big.thumbnail((DETECT_SIZE, DETECT_SIZE), Image.Resampling.BILINEAR)
    im = big.copy()
    im.thumbnail((ANALYSIS_SIZE, ANALYSIS_SIZE), Image.Resampling.BILINEAR)
    found: list[Face] = []
    checked = False
    if faces is not None and faces.available:
        try:
            found = faces.detect(np.asarray(big))
            checked = True
        except Exception as exc:  # noqa: BLE001
            log.warning("face detection failed: %s", exc)
    gray = ImageOps.grayscale(im)
    gray.thumbnail((512, 512))
    g = np.asarray(gray)
    lum = g.astype(np.float32) / 255.0
    return Quality(
        sharpness=round(sharpness(g, found), 4),
        brightness=round(float(lum.mean()), 4),
        dark_clip=round(float((lum < 0.03).mean()), 4),
        bright_clip=round(float((lum > 0.97).mean()), 4),
        faces=found,
        faces_checked=checked,
    )


# ----------------------------------------------------------------- verdicts
REASONS = {
    "blurry": ("Blurry", "🌫️"),
    "eyes-closed": ("Eyes closed", "😑"),
    "too-dark": ("Too dark", "🌑"),
    "too-bright": ("Too bright", "☀️"),
}


@dataclass
class QualityRules:
    blur: bool = True
    eyes_closed: bool = True
    exposure: bool = True
    blur_threshold: float = 0.5
    blink_threshold: float = 0.5
    smile_threshold: float = 0.5
    dark_threshold: float = 0.18  # mean luminance below (and lots of crushed blacks)
    bright_threshold: float = 0.85


def verdict(q: Quality, r: QualityRules) -> tuple[str | None, list[str], bool]:
    """Return (first reject reason or None, all flags, smiling)."""
    flags = []
    if r.blur and q.sharpness < r.blur_threshold:
        flags.append("blurry")
    if r.eyes_closed and any(f.blink >= r.blink_threshold for f in q.faces):
        flags.append("eyes-closed")
    if r.exposure:
        if q.brightness < r.dark_threshold and q.dark_clip > 0.25:
            flags.append("too-dark")
        elif q.brightness > r.bright_threshold and q.bright_clip > 0.25:
            flags.append("too-bright")
    smiling = bool(q.faces) and all(f.smile >= r.smile_threshold for f in q.faces)
    return (flags[0] if flags else None), flags, smiling


def summary(q: Quality, r: QualityRules) -> dict:
    reason, flags, smiling = verdict(q, r)
    return {
        "sharpness": q.sharpness,
        "brightness": q.brightness,
        "faces": len(q.faces),
        "blink": max((f.blink for f in q.faces), default=None),
        "smile": min((f.smile for f in q.faces), default=None),
        "flags": flags,
        "smiling": smiling,
        "faces_checked": q.faces_checked,
    }
