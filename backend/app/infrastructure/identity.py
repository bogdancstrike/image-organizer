"""Thread-local OpenCV YuNet/SFace model adapter."""
from __future__ import annotations
import logging
import os
import threading
from pathlib import Path
import numpy as np
from PIL import Image
from app.recognition.people import FaceID, DETECT_SIZE, MIN_FACE_PX
log = logging.getLogger(__name__)

class FaceIdentifier:
    """Thread-local detector/recognizer instances (OpenCV DNN objects are not thread-safe)."""

    def __init__(self, detector: str | None, recognizer: str | None):
        ok = bool(detector and recognizer and Path(detector).exists() and Path(recognizer).exists())
        self.detector, self.recognizer = (detector, recognizer) if ok else (None, None)
        self._local = threading.local()
        if not ok:
            log.warning("face identity models not found: 'By person' disabled")

    @property
    def available(self) -> bool:
        return self.detector is not None

    def _models(self):
        if getattr(self._local, "det", None) is None:
            import cv2

            self._local.det = cv2.FaceDetectorYN.create(self.detector, "", (320, 320), 0.8)
            self._local.rec = cv2.FaceRecognizerSF.create(self.recognizer, "")
        return self._local.det, self._local.rec

    def _detect(self, img: Image.Image):
        import cv2

        rgb = img.convert("RGB")
        rgb.thumbnail((DETECT_SIZE, DETECT_SIZE))
        bgr = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)
        h, w = bgr.shape[:2]
        det, _ = self._models()
        det.setInputSize((w, h))
        _, faces = det.detect(bgr)
        return bgr, faces if faces is not None else []

    def locate(self, img: Image.Image) -> list[tuple[tuple[float, float, float, float], float]]:
        """Detection only: quality analysis does not need identity embeddings."""
        bgr, faces = self._detect(img)
        h, w = bgr.shape[:2]
        return [((max(0.,float(f[0])/w),max(0.,float(f[1])/h),
                  min(1.,float(f[0]+f[2])/w),min(1.,float(f[1]+f[3])/h)),float(f[-1]) if len(f)>=15 else 1.)
                for f in faces if min(f[2],f[3]) >= MIN_FACE_PX]

    def identify(self, img: Image.Image) -> list[FaceID]:
        bgr, faces = self._detect(img)
        h, w = bgr.shape[:2]
        _, rec = self._models()
        out = []
        for f in faces if faces is not None else []:
            x, y, fw, fh = (float(v) for v in f[:4])
            if min(fw, fh) < MIN_FACE_PX:
                continue
            emb = rec.feature(rec.alignCrop(bgr, f)).flatten().astype(np.float32)
            emb /= np.linalg.norm(emb) or 1.0
            box = (max(0.0, x / w), max(0.0, y / h), min(1.0, (x + fw) / w), min(1.0, (y + fh) / h))
            reliable = True
            confidence = 1.0
            if len(f) >= 15:
                points = f[4:14].reshape(5, 2)
                eye = points[1] - points[0]
                span = float(np.linalg.norm(eye))
                mid = (points[0] + points[1]) / 2
                yaw = abs(float(np.dot(points[2] - mid, eye / (span + 1e-6)))) / (span + 1e-6)
                confidence = float(f[-1])
                reliable = confidence >= .90 and span / fw > .25 and yaw < .35 and min(fw, fh) >= 60
            out.append(FaceID(round(fw * fh / (w * h), 5), tuple(round(v, 4) for v in box), emb, reliable, confidence))
        return out


_ident: FaceIdentifier | None = None
_lock = threading.Lock()


def get_face_identifier() -> FaceIdentifier:
    global _ident
    with _lock:
        if _ident is None:
            d = os.environ.get("FACE_ID_DIR", "/models")
            _ident = FaceIdentifier(f"{d}/face_detection_yunet_2023mar.onnx", f"{d}/face_recognition_sface_2021dec.onnx")
        return _ident


