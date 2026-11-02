"""Bundled MIT-licensed LAION aesthetic head; CPU NumPy, no runtime download or PyTorch.

Only accepts normalized OpenAI CLIP ViT-B/32 projected image embeddings. Similar
dimensions in another encoder do not imply the same space. See adjacent model provenance.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

SPACE = "openai/clip-vit-base-patch32"
WEIGHTS = Path(__file__).parent / "models/laion_aesthetic/weights.json"
CHECKSUM = "fbd3047102bc48da26afb272a215a7db3b872c5d5c511972d4c5ee44b4863ef2"
VERSION = "laion-v1-b32:" + CHECKSUM[:16]


class AestheticPredictor:
    def __init__(self, path: Path = WEIGHTS):
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != CHECKSUM:
            raise ValueError("aesthetic model checksum mismatch")
        data = json.loads(raw)
        self.weight = np.asarray(data["weight"], dtype=np.float32)
        self.bias = float(data["bias"])

    def predict(self, embeddings: np.ndarray, space: str) -> np.ndarray:
        X = np.asarray(embeddings, dtype=np.float32)
        if space != SPACE or X.ndim != 2 or X.shape[1] != 512:
            raise ValueError("aesthetic model requires verified OpenAI CLIP ViT-B/32 embeddings")
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        if not np.isfinite(X).all() or np.any(norms <= 1e-8):
            raise ValueError("invalid aesthetic embedding")
        return ((X / norms) @ self.weight + self.bias).astype(np.float32)


@lru_cache(maxsize=1)
def get_predictor() -> AestheticPredictor:
    return AestheticPredictor()
