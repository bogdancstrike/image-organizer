"""OCR signal (RapidOCR, ONNX, CPU): how much readable text a photo contains, plus a snippet for search."""
from __future__ import annotations

import logging
import threading

import numpy as np
from PIL import Image

log = logging.getLogger(__name__)
OCR_SIZE = 960

TEXT_KEYWORDS = ("text", "caption", "document", "receipt", "invoice", "note", "slide", "chart", "meme", "screenshot",
                 "ticket", "quote", "whiteboard")


class TextReader:
    def __init__(self):
        self._local = threading.local()
        try:
            import rapidocr_onnxruntime  # noqa: F401

            self.available = True
        except Exception:  # noqa: BLE001
            self.available = False
            log.warning("rapidocr not installed: OCR disabled")

    def _engine(self):
        if getattr(self._local, "ocr", None) is None:
            from rapidocr_onnxruntime import RapidOCR

            self._local.ocr = RapidOCR()
        return self._local.ocr

    def read(self, img: Image.Image) -> dict:
        """Returns {"chars", "coverage" (share of the image covered by text boxes), "text" (≤ 300 chars)}."""
        im = img.convert("RGB")
        im.thumbnail((OCR_SIZE, OCR_SIZE))
        res, _ = self._engine()(np.asarray(im))
        if not res:
            return {"chars": 0, "coverage": 0.0, "text": ""}
        w, h = im.size
        area = 0.0
        words = []
        for box, text, score in res:
            if float(score) < 0.5:
                continue
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            area += (max(xs) - min(xs)) * (max(ys) - min(ys))
            words.append(str(text))
        text = " ".join(words)
        return {"chars": len(text.replace(" ", "")), "coverage": round(min(1.0, area / (w * h)), 4), "text": text[:300]}


_reader: TextReader | None = None
_lock = threading.Lock()


def get_text_reader() -> TextReader:
    global _reader
    with _lock:
        if _reader is None:
            _reader = TextReader()
        return _reader


def text_category(categories: list[dict]) -> list[dict]:
    """Categories in a set that are about text (documents, captions, screenshots…)."""
    return [c for c in categories if c["id"] == "ids" or any(k in f"{c['id']} {c['name']}".lower() for k in TEXT_KEYWORDS)]
