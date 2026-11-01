"""Face identities for the "By person" strategy: OpenCV YuNet (detector) + SFace (128-d identity embeddings).

Both models are Apache-2.0 and run on CPU. Embeddings are cached; clustering happens per sort.
"""
from __future__ import annotations

import io
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

log = logging.getLogger(__name__)

DETECT_SIZE = 1280
MIN_FACE_PX = 36  # smaller faces carry no usable identity
SAME_PERSON = 0.363  # SFace cosine threshold recommended by OpenCV


@dataclass
class FaceID:
    area: float  # share of the image
    box: tuple[float, float, float, float]  # x0, y0, x1, y1 normalized
    emb: np.ndarray  # 128-d, L2-normalized

    def to_dict(self) -> dict:
        return {"area": self.area, "box": list(self.box), "emb": [round(float(x), 5) for x in self.emb]}

    @classmethod
    def from_dict(cls, d: dict) -> "FaceID":
        return cls(d["area"], tuple(d["box"]), np.asarray(d["emb"], dtype=np.float32))


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

    def identify(self, img: Image.Image) -> list[FaceID]:
        import cv2

        rgb = img.convert("RGB")
        rgb.thumbnail((DETECT_SIZE, DETECT_SIZE))
        bgr = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)
        h, w = bgr.shape[:2]
        det, rec = self._models()
        det.setInputSize((w, h))
        _, faces = det.detect(bgr)
        out = []
        for f in faces if faces is not None else []:
            x, y, fw, fh = (float(v) for v in f[:4])
            if min(fw, fh) < MIN_FACE_PX:
                continue
            emb = rec.feature(rec.alignCrop(bgr, f)).flatten().astype(np.float32)
            emb /= np.linalg.norm(emb) or 1.0
            box = (max(0.0, x / w), max(0.0, y / h), min(1.0, (x + fw) / w), min(1.0, (y + fh) / h))
            out.append(FaceID(round(fw * fh / (w * h), 5), tuple(round(v, 4) for v in box), emb))
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


def cluster_people(embs: np.ndarray, threshold: float = SAME_PERSON) -> np.ndarray:
    """Agglomerative clustering (average linkage, cosine) cut at the same-person threshold. Returns a label per face."""
    if len(embs) <= 1:
        return np.zeros(len(embs), int)
    from sklearn.cluster import AgglomerativeClustering
    from threadpoolctl import threadpool_limits

    with threadpool_limits(limits=2):
        model = AgglomerativeClustering(
            n_clusters=None, metric="cosine", linkage="average", distance_threshold=1.0 - threshold
        )
        return model.fit_predict(embs).astype(int)


def face_crop_webp(img: Image.Image, box: tuple[float, float, float, float], size: int = 160) -> bytes:
    """Square crop around a face (with some margin) as a WebP avatar."""
    w, h = img.size
    x0, y0, x1, y1 = box[0] * w, box[1] * h, box[2] * w, box[3] * h
    cx, cy, side = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) * 1.6
    crop = img.convert("RGB").crop((int(cx - side / 2), int(cy - side / 2), int(cx + side / 2), int(cy + side / 2)))
    crop.thumbnail((size, size))
    buf = io.BytesIO()
    crop.save(buf, "WEBP", quality=82)
    return buf.getvalue()


# ---------------------------------------------------------------- people without a visible face
PRESENT_PROMPTS = [
    "a photo of a person", "a photo of a man", "a photo of a woman", "a photo of a couple", "a person seen from behind",
    "a small figure of a person in a landscape", "a close-up of a person's hands", "a person's legs and feet walking",
    "a woman wearing a wedding dress", "a man wearing a suit", "a woman wearing a veil", "two people holding hands",
]
ABSENT_PROMPTS = [
    "a landscape with no people", "an empty mountain meadow", "rocks, grass and trees", "an empty room", "a photo of an object",
    "a wedding dress hanging on a tree with nobody wearing it", "clothes on a hanger", "a pair of empty shoes", "a still life",
    "a photo of food", "a photo of an animal", "a document or screenshot", "an empty street", "a building",
]
MAN_PROMPTS = ["a photo of a man", "a man's legs in dark trousers and boots", "a man in a dark suit", "a man's hand in a suit sleeve",
               "a bearded man", "men's boots"]
WOMAN_PROMPTS = ["a photo of a woman", "a woman in a white dress", "a woman's hand with a ring and lace sleeve", "a woman under a veil",
                 "a woman with long hair", "a bride's dress and train"]


def _enc(embedder, prompts):
    v = np.asarray(embedder.embed_texts(prompts), dtype=np.float32)
    return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)


def text_bank(embedder) -> dict[str, np.ndarray]:
    return {"present": _enc(embedder, PRESENT_PROMPTS), "absent": _enc(embedder, ABSENT_PROMPTS),
            "man": _enc(embedder, MAN_PROMPTS), "woman": _enc(embedder, WOMAN_PROMPTS)}


def _softmax_share(X: np.ndarray, a: np.ndarray, b: np.ndarray, temperature: float = 100.0) -> np.ndarray:
    logits = temperature * np.hstack([X @ a.T, X @ b.T])
    logits -= logits.max(axis=1, keepdims=True)
    p = np.exp(logits)
    p /= p.sum(axis=1, keepdims=True)
    return p[:, : len(a)].sum(axis=1)


def person_presence(X: np.ndarray, bank: dict[str, np.ndarray]) -> np.ndarray:
    """P(someone is in the photo) per image (zero-shot: people vs. no-people prompts)."""
    return _softmax_share(X, bank["present"], bank["absent"])


def man_probability(X: np.ndarray, bank: dict[str, np.ndarray]) -> np.ndarray:
    """P(the visible person reads as a man) per image."""
    return _softmax_share(X, bank["man"], bank["woman"])


def assign_by_appearance(Xc: np.ndarray, protos: np.ndarray, proto_man: np.ndarray, p_man: np.ndarray,
                         decisive: float = 0.2, min_sim: float = -0.05, present: np.ndarray | None = None) -> list[tuple[int, float, list[int]]]:
    """Faceless photos → known people.

    Xc / protos are *shoot-centered* embeddings (the look every photo shares — B&W, location, light — removed), so what
    is left describes the person: outfit, build, hair. When the known people differ in gender and a photo clearly reads
    as one, only people of that gender are candidates; among candidates the closest appearance wins.
    Returns per photo (best index or -1, similarity, all candidates within reach — for "copy" mode).
    """
    if len(protos) == 0:
        return [(-1, 0.0, []) for _ in range(len(Xc))]
    mixed = proto_man.max() - proto_man.min() > 0.3
    sim = Xc @ protos.T
    out = []
    sure = present if present is not None else np.zeros(len(Xc))
    for row, pm, pr in zip(sim, p_man, sure):
        cand = list(range(len(protos)))
        if mixed and abs(pm - 0.5) >= decisive:
            same = [i for i in cand if (proto_man[i] > 0.5) == (pm > 0.5)]
            cand = same or cand
        best = max(cand, key=lambda i: row[i])
        # a decisive gender match needs only a non-negative appearance match; otherwise appearance must speak
        # someone is clearly in the photo, or gender settles it: the closest candidate gets it
        need = -1.0 if (pr >= 0.85 or (mixed and abs(pm - 0.5) >= decisive and len(cand) == 1)) else min_sim
        if row[best] < need:
            out.append((-1, float(row[best]), []))
            continue
        close = [i for i in range(len(protos)) if row[i] >= min_sim and row[i] >= row[best] - 0.03]
        out.append((int(best), float(row[best]), close))
    return out
