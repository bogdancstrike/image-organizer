"""Thread-local MediaPipe model adapter for face quality measurements."""
from __future__ import annotations
import logging
import os
import threading
from pathlib import Path
import numpy as np
from PIL import Image
from app.culling.quality import Face, MIN_FACE_AREA, ANALYSIS_SIZE, _expression
log = logging.getLogger(__name__)
FACE_MODEL_ENV = "FACE_MODEL"

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
                _expression(sc, lms),
            ))
        return out

    def detect(self, rgb: np.ndarray) -> list[Face]:
        """MediaPipe's detector is short-range (selfie-sized faces). To find faces in full-body and
        group shots we also run it on overlapping 2x2 and 3x3 tiles and merge the results."""
        H, W = rgb.shape[:2]
        found: list[Face] = []

        def add(box, blink, smile, expr=None):
            x0, y0, x1, y1 = (max(0.0, box[0]), max(0.0, box[1]), min(1.0, box[2]), min(1.0, box[3]))
            area = (x1 - x0) * (y1 - y0)
            if area < MIN_FACE_AREA:
                return
            for i, f in enumerate(found):
                if _iou(f.box, (x0, y0, x1, y1)) > 0.3:
                    if area > f.area:  # keep the better-resolved detection
                        found[i] = Face(round(blink, 3), round(smile, 3), round(area, 5), (x0, y0, x1, y1), expr)
                    return
            found.append(Face(round(blink, 3), round(smile, 3), round(area, 5), (x0, y0, x1, y1), expr))

        full = Image.fromarray(rgb)
        small = full.copy()
        small.thumbnail((ANALYSIS_SIZE, ANALYSIS_SIZE))
        for box, blink, smile, expr in self._detect_one(np.asarray(small)):
            add(box, blink, smile, expr)
        for n in (2, 3):
            tw, th = W / n, H / n
            ox, oy = tw * 0.25, th * 0.25  # 25% overlap
            for i in range(n):
                for j in range(n):
                    x0, y0 = max(0, int(j * tw - ox)), max(0, int(i * th - oy))
                    x1, y1 = min(W, int((j + 1) * tw + ox)), min(H, int((i + 1) * th + oy))
                    tile = full.crop((x0, y0, x1, y1))
                    tile.thumbnail((ANALYSIS_SIZE, ANALYSIS_SIZE))
                    for (bx0, by0, bx1, by1), blink, smile, expr in self._detect_one(np.asarray(tile)):
                        cw, ch = x1 - x0, y1 - y0
                        add(((x0 + bx0 * cw) / W, (y0 + by0 * ch) / H, (x0 + bx1 * cw) / W, (y0 + by1 * ch) / H), blink, smile, expr)
        # YuNet complements the short-range landmark detector. Rotation recovers tilted/profile faces.
        from app.infrastructure.identity import get_face_identifier
        try:
            identifier = get_face_identifier()
            if identifier.available:
                detected = identifier.locate(full)
                if not found and not detected:
                    for angle in (90, 270, 180):
                        rotated = identifier.locate(full.rotate(angle, expand=True))
                        if rotated:
                            detected = [(unrotate_box(box, angle), confidence) for box, confidence in rotated]
                            break
                for box, confidence in detected:
                    area = (box[2]-box[0])*(box[3]-box[1])
                    if confidence < .8 or area < MIN_FACE_AREA or any(_iou(face.box, box) > .3 for face in found):
                        continue
                    found.append(Face(0., 0., round(area,5), box, landmarks_checked=False))
        except Exception as exc:  # Optional fallback must not discard valid landmark detections.
            log.warning("fallback face detection failed: %s", exc)
        for f in found:
            f.box = tuple(round(v, 4) for v in f.box)
        return found


def unrotate_box(box, angle):
    x0,y0,x1,y1 = box
    return {90:(1-y1,x0,1-y0,x1),270:(y0,1-x1,y1,1-x0),180:(1-x1,1-y1,1-x0,1-y0)}[angle]


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


