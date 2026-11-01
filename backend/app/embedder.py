"""CLIP embeddings via fastembed (ONNX, CPU). Spec: REQ-ANL-2."""
from __future__ import annotations

import threading
from typing import Protocol

import numpy as np
from PIL import Image

VISION_MODEL = "Qdrant/clip-ViT-B-32-vision"
TEXT_MODEL = "Qdrant/clip-ViT-B-32-text"


def normalize(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float32)
    if a.ndim == 1:
        n = np.linalg.norm(a)
        return a / n if n > 0 else a
    n = np.linalg.norm(a, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return a / n


class Embedder(Protocol):
    def embed_images(self, images: list[Image.Image]) -> np.ndarray: ...

    def embed_texts(self, texts: list[str]) -> np.ndarray: ...


class ClipEmbedder:
    """Shared image/text CLIP space. Thread-safe; text embeddings are memoized."""

    def __init__(self, cache_dir: str | None = None, threads: int | None = None):
        from fastembed import ImageEmbedding, TextEmbedding

        self._img = ImageEmbedding(VISION_MODEL, cache_dir=cache_dir, threads=threads)
        self._txt = TextEmbedding(TEXT_MODEL, cache_dir=cache_dir, threads=threads)
        self._lock = threading.Lock()
        self._text_cache: dict[str, np.ndarray] = {}

    def embed_images(self, images: list[Image.Image]) -> np.ndarray:
        if not images:
            return np.zeros((0, 512), dtype=np.float32)
        with self._lock:
            vecs = list(self._img.embed(images, batch_size=32))
        return normalize(np.vstack(vecs))

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        missing = [t for t in dict.fromkeys(texts) if t not in self._text_cache]
        if missing:
            with self._lock:
                vecs = list(self._txt.embed(missing, batch_size=64))
            for t, v in zip(missing, vecs):
                self._text_cache[t] = normalize(np.asarray(v))
        return np.vstack([self._text_cache[t] for t in texts]) if texts else np.zeros((0, 512), np.float32)


_singleton: ClipEmbedder | None = None
_singleton_lock = threading.Lock()


def get_clip_embedder(cache_dir: str | None = None) -> ClipEmbedder:
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = ClipEmbedder(cache_dir=cache_dir)
        return _singleton
