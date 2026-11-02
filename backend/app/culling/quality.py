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
from dataclasses import asdict, dataclass, field

import numpy as np
from PIL import Image, ImageOps
from app.culling.ports import FaceDetector

log = logging.getLogger(__name__)

ANALYSIS_SIZE = 1024
DETECT_SIZE = 2048  # faces are searched on this resolution (tiled)
MIN_FACE_AREA = 0.0006  # ignore tiny background faces (eyes unreadable)


@dataclass
class Face:
    blink: float  # 0..1, mean of both eyes
    smile: float  # 0..1
    area: float  # share of the image area
    box: tuple[float, float, float, float]  # x0, y0, x1, y1 normalized
    # expression (MediaPipe blendshapes + head pose), 0..1: gaze away from camera, mouth open (mid-word), frown, squint, head turn
    expr: dict | None = None
    sharpness: float | None = None  # focus in this face's eye region; None for unreadably small detections


@dataclass
class Quality:
    sharpness: float  # 0..1
    brightness: float  # 0..1 mean luminance
    dark_clip: float  # share of pixels < 3%
    bright_clip: float  # share of pixels > 97%
    faces: list[Face] = field(default_factory=list)
    faces_checked: bool = False
    noise: float = 0.0  # Immerkær noise sigma (0..1), edges excluded
    tilt: float | None = None  # degrees of a consistent near-horizontal line structure, None if there is none
    v: int = 1  # analysis version: cached entries older than QUALITY_VERSION are recomputed
    features: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Quality":
        faces = [Face(**{**f, "box": tuple(f["box"])}) for f in d.get("faces", [])]
        return cls(d["sharpness"], d["brightness"], d["dark_clip"], d["bright_clip"], faces, d.get("faces_checked", False),
                   d.get("noise", 0.0), d.get("tilt"), d.get("v", 1), d.get("features", {}))


QUALITY_VERSION = 5  # 5: thumbnail clarity, crop dimensions, gradients and compression indicators


def _expression(sc: dict, lms) -> dict:
    """Expression signals from MediaPipe blendshapes; head turn (yaw) from the nose tip vs. the eye corners."""
    gaze = max(
        (sc.get("eyeLookOutLeft", 0) + sc.get("eyeLookInRight", 0)) / 2,
        (sc.get("eyeLookInLeft", 0) + sc.get("eyeLookOutRight", 0)) / 2,
        (sc.get("eyeLookUpLeft", 0) + sc.get("eyeLookUpRight", 0)) / 2,
        (sc.get("eyeLookDownLeft", 0) + sc.get("eyeLookDownRight", 0)) / 2,
    )
    yaw = 0.0
    try:
        nose, le, re = lms[1], lms[33], lms[263]
        span = abs(re.x - le.x) or 1e-6
        yaw = min(1.0, abs((nose.x - (le.x + re.x) / 2) / span) * 2)
    except (IndexError, AttributeError):
        pass
    return {
        "gaze": round(float(gaze), 3),
        "mouth": round(float(sc.get("jawOpen", 0)), 3),
        "frown": round(float((sc.get("mouthFrownLeft", 0) + sc.get("mouthFrownRight", 0)) / 2 + sc.get("browDownLeft", 0) * 0.25), 3),
        "squint": round(float((sc.get("eyeSquintLeft", 0) + sc.get("eyeSquintRight", 0)) / 2), 3),
        "yaw": round(float(yaw), 3),
    }


def _lap_var(gray: np.ndarray) -> float:
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    g = gray.astype(np.float32)
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(lap.var())


def noise_sigma(gray: np.ndarray) -> float:
    """Immerkær fast noise estimate on a grayscale image, ignoring strong edges (texture is not noise)."""
    import cv2

    g = gray.astype(np.float32)
    m = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], np.float32)
    r = cv2.filter2D(g, -1, m)[1:-1, 1:-1]
    edges = cv2.Canny(gray.astype(np.uint8), 60, 150)[1:-1, 1:-1] > 0
    vals = np.abs(r[~edges])
    if vals.size == 0:
        return 0.0
    return float(math.sqrt(math.pi / 2) * vals.mean() / 6 / 255)


def horizon_tilt(gray: np.ndarray) -> float | None:
    """Angle of a *consistent* set of long near-horizontal lines (horizons, tables, window sills).
    Returns None when there is no such structure (organic slopes disagree and are ignored)."""
    import cv2

    h, w = gray.shape
    lines = cv2.HoughLinesP(cv2.Canny(gray, 50, 150), 1, np.pi / 360, threshold=80, minLineLength=int(w * 0.45), maxLineGap=8)
    if lines is None:
        return None
    angs = []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        a = math.degrees(math.atan2(y2 - y1, x2 - x1))
        a = a - 180 if a > 90 else a + 180 if a < -90 else a
        if abs(a) < 10:
            angs.append(a)
    if len(angs) < 3 or float(np.std(angs)) > 1.5:
        return None
    return round(float(np.median(angs)), 2)


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


def perceptual_signals(gray: np.ndarray, faces: list[Face]) -> dict[str, float]:
    """Lightweight image-quality heuristics, not a calibrated aesthetic predictor."""
    import cv2

    g = gray.astype(np.float32)
    if min(g.shape) < 8:
        return {"detail": .5, "balance": .5, "separation": .5}
    fine = _lap_var(g)
    coarse = _lap_var(cv2.resize(g, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA))
    detail = min(1.0, coarse / (fine * .5 + 1e-6)) if fine > 1 else 0.0
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)
    energy = np.hypot(gx, gy)
    total = float(energy.sum())
    h, w = g.shape
    if total < 1e-6:
        return {"detail": round(detail, 3), "balance": .5, "separation": .5}
    yy, xx = np.mgrid[:h, :w]
    cx, cy = float((xx * energy).sum() / total / w), float((yy * energy).sum() / total / h)
    distance = min(math.hypot(cx - x, cy - y) for x, y in ((.5,.5),(1/3,1/3),(2/3,1/3),(1/3,2/3),(2/3,2/3)))
    border = np.ones((h,w),bool); border[h//10:-h//10, w//10:-w//10] = False
    edge_ratio = float(energy[border].mean()) / (float(energy[~border].mean()) + 1e-6)
    balance = np.clip(1 - distance * 1.5 - max(0, edge_ratio - 1.5) * .15, 0, 1)
    mask = np.zeros((h,w),bool)
    for face in faces:
        x0,y0,x1,y1=face.box
        mask[max(0,int(y0*h)):min(h,int(y1*h)+1), max(0,int(x0*w)):min(w,int(x1*w)+1)] = True
    if mask.any() and (~mask).any():
        ratio = float(energy[mask].mean()) / (float(energy[~mask].mean()) + 1e-6)
    else:
        cutoff = np.percentile(energy, 75)
        salient = energy >= cutoff
        ratio = float(energy[salient].mean()) / (float(energy[~salient].mean()) + 1e-6) if (~salient).any() else 1.0
    separation = np.clip(ratio / (ratio + 2), 0, 1)
    return {"detail": round(float(detail),3), "balance": round(float(balance),3), "separation": round(float(separation),3)}


def advanced_signals(rgb: np.ndarray, gray: np.ndarray, width: int, height: int) -> dict[str, float]:
    """Weak, inspectable signals. Directional edges are not proof of unwanted motion blur."""
    import cv2
    g = gray.astype(np.float32)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    xx, yy, xy = float((gx*gx).mean()), float((gy*gy).mean()), float((gx*gy).mean())
    tenengrad = min(1., math.log10(1+xx+yy)/5)
    direction = math.sqrt((xx-yy)**2+4*xy*xy)/(xx+yy+1e-6)
    dx, dy = np.abs(np.diff(g, axis=1)), np.abs(np.diff(g, axis=0))
    boundaries = np.concatenate([dx[:, 7::8].ravel(), dy[7::8, :].ravel()])
    ordinary = np.concatenate([dx[:, 3::8].ravel(), dy[3::8, :].ravel()])
    blocking = min(1., max(0., (float(boundaries.mean())-float(ordinary.mean()))/25)) if len(boundaries) and len(ordinary) else 0.
    thumbnail = cv2.resize(gray, (96, 96), interpolation=cv2.INTER_AREA)
    thumb = _norm_sharp(_lap_var(thumbnail))
    p5, p95 = np.percentile(g, [5, 95]); contrast = min(1., float(p95-p5)/150)
    colors = rgb.astype(np.float32)/255
    chroma = colors.max(axis=2)-colors.min(axis=2)
    color = .5 if float(chroma.mean()) < .035 else float(np.clip(1-abs(float(chroma.mean())-.25)*1.5, .2, 1))
    return {"tenengrad": round(tenengrad,3), "directionality": round(direction,3), "blocking": round(blocking,3),
            "thumbnail": round(thumb,3), "contrast": round(contrast,3), "color": round(color,3),
            "aspect_ratio": width/max(1,height), "resolution": min(1., math.sqrt(width*height/(1080*1350)))}


def analyze_image(img: Image.Image, faces: FaceDetector | None) -> Quality:
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
    face_gray = np.asarray(ImageOps.grayscale(big))
    for face in found:
        x0, y0, x1, y1 = face.box
        crop = face_gray[int(y0 * face_gray.shape[0]):int((y0 + (y1 - y0) * .6) * face_gray.shape[0]) + 1,
                         int(x0 * face_gray.shape[1]):int(x1 * face_gray.shape[1]) + 1]
        if crop.size >= 400:
            face.sharpness = round(_norm_sharp(_lap_var(crop)), 4)
    return Quality(
        features={**perceptual_signals(g, found), **advanced_signals(np.asarray(im), g, img.width, img.height)},
        noise=round(noise_sigma(g), 4),
        tilt=horizon_tilt(g),
        sharpness=round(sharpness(g, found), 4),
        brightness=round(float(lum.mean()), 4),
        dark_clip=round(float((lum < 0.03).mean()), 4),
        bright_clip=round(float((lum > 0.97).mean()), 4),
        faces=found,
        faces_checked=checked,
        v=QUALITY_VERSION,
    )


# ----------------------------------------------------------------- verdicts
REASONS = {
    "blurry": ("Blurry", "🌫️"),
    "eyes-closed": ("Eyes closed", "😑"),
    "too-dark": ("Too dark", "🌑"),
    "too-bright": ("Too bright", "☀️"),
    "noisy": ("Noisy", "🌪️"),
    "tilted": ("Tilted horizon", "📐"),
    "cropped-face": ("Face cut off", "✂️"),
    "burst": ("Burst extras", "🎞️"),  # not a verdict flag: assigned by best-of-burst selection
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
    faces_rule: str = "any"  # "any" face or only the "main" (largest) face counts for eyes/smile
    noise_check: bool = False
    noise_threshold: float = 0.045
    tilt_check: bool = False
    tilt_tolerance: float = 1.5  # degrees
    face_crop: bool = False  # a face cut by the frame edge


def _faces(q: Quality, r: QualityRules) -> list[Face]:
    if r.faces_rule == "main" and q.faces:
        return [max(q.faces, key=lambda f: f.area)]
    return q.faces


def verdict(q: Quality, r: QualityRules) -> tuple[str | None, list[str], bool]:
    """Return (first reject reason or None, all flags, smiling)."""
    flags = []
    if r.blur and q.sharpness < r.blur_threshold:
        flags.append("blurry")
    faces = _faces(q, r)
    if r.eyes_closed and any(f.blink >= r.blink_threshold for f in faces):
        flags.append("eyes-closed")
    if r.exposure:
        if q.brightness < r.dark_threshold and q.dark_clip > 0.25:
            flags.append("too-dark")
        elif q.brightness > r.bright_threshold and q.bright_clip > 0.25:
            flags.append("too-bright")
    if r.noise_check and q.noise > r.noise_threshold:
        flags.append("noisy")
    if r.tilt_check and q.tilt is not None and r.tilt_tolerance <= abs(q.tilt) <= 8:
        flags.append("tilted")
    if r.face_crop and any(
        f.area > 0.01 and (f.box[0] < 0.005 or f.box[2] > 0.995 or f.box[1] < 0.003) for f in faces
    ):
        flags.append("cropped-face")
    smiling = bool(faces) and all(f.smile >= r.smile_threshold for f in faces)
    return (flags[0] if flags else None), flags, smiling


def score(q: Quality, r: QualityRules) -> float:
    """0..1 overall keeper score: sharpness, exposure, eyes open, smile. Rejected shots are halved."""
    sharp = min(1.0, max(0.0, (q.sharpness - 0.3) / 0.5))
    exposure = (1 - min(1.0, abs(q.brightness - 0.45) / 0.45)) * (1 - min(0.5, q.dark_clip + q.bright_clip))
    faces = _faces(q, r)
    if faces:
        eyes = 1 - max(f.blink for f in faces)
        smile = sum(f.smile for f in faces) / len(faces)
        s = 0.45 * sharp + 0.15 * exposure + 0.25 * eyes + 0.15 * smile
    else:
        s = 0.7 * sharp + 0.3 * exposure
    if verdict(q, r)[0]:
        s *= 0.5
    return round(max(0.0, min(1.0, s)), 3)


def stars(s: float) -> int:
    return max(1, min(5, 1 + round(s * 4)))


def find_bursts(items: list[tuple[str, str, float, "np.ndarray"]], seconds: float, similarity: float) -> dict[str, int]:
    """items: (id, folder, timestamp, embedding). Consecutive shots in the same folder taken within `seconds`
    of each other and looking alike (CLIP cosine >= similarity) form a burst. Returns {id: group} for bursts of 2+."""
    order = sorted(items, key=lambda t: (t[1], t[2]))
    groups: dict[str, int] = {}
    gid = 0
    run: list[str] = []
    for prev, cur in zip([None] + order[:-1], order):
        linked = (
            prev is not None and prev[1] == cur[1] and abs(cur[2] - prev[2]) <= seconds
            and float(np.dot(prev[3], cur[3])) >= similarity
        )
        if linked:
            run.append(cur[0])
        else:
            if len(run) > 1:
                gid += 1
                groups.update({i: gid for i in run})
            run = [cur[0]]
    if len(run) > 1:
        gid += 1
        groups.update({i: gid for i in run})
    return groups


def summary(q: Quality, r: QualityRules) -> dict:
    reason, flags, smiling = verdict(q, r)
    sc = score(q, r)
    return {
        "score": sc,
        "rating": round(1 + sc * 4, 2),
        "stars": stars(sc),
        "sharpness": q.sharpness,
        "brightness": q.brightness,
        "faces": len(q.faces),
        "faces_considered": len(_faces(q, r)),
        "eyes_open": sum(f.blink < r.blink_threshold for f in _faces(q, r)),
        "aspect_ratio": q.features.get("aspect_ratio", 1.),
        "face_regions": [{"box": list(f.box), "sharpness": f.sharpness, "blink": f.blink} for f in q.faces],
        "blink": max((f.blink for f in q.faces), default=None),
        "smile": min((f.smile for f in q.faces), default=None),
        "flags": flags,
        "smiling": smiling,
        "faces_checked": q.faces_checked,
        "noise": q.noise,
        "tilt": q.tilt,
    }
