"""Embedding contract and vector operations shared by recognition and model adapters."""
from __future__ import annotations

from typing import Protocol
import numpy as np
from PIL import Image

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


