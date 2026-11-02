"""CLIP embeddings via fastembed (ONNX, CPU). Spec: REQ-ANL-2."""
from __future__ import annotations

import os
import threading

import numpy as np
from PIL import Image

from app.recognition.ports import normalize

VISION_MODEL = "Qdrant/clip-ViT-B-32-vision"
TEXT_MODEL = "Qdrant/clip-ViT-B-32-text"
# selectable recognition models: (vision, text). SigLIP 2 is slower (~5x) but understands scenes and styles better.
MODELS = {
    "clip": (VISION_MODEL, TEXT_MODEL),
    "siglip2": ("google/siglip2-base-patch16-224", "google/siglip2-base-patch16-224"),
}


def execution_providers(device: str = "cpu") -> list[str]:
    if device == "cpu":
        return ["CPUExecutionProvider"]
    if device != "gpu":
        raise ValueError("DEVICE must be cpu or gpu")
    import onnxruntime as ort

    if hasattr(ort, "preload_dlls"):
        ort.preload_dlls(directory="")
    if "CUDAExecutionProvider" not in ort.get_available_providers():
        raise RuntimeError("DEVICE=gpu requires the GPU image, an NVIDIA GPU and NVIDIA Container Toolkit. "
                           "Set DEVICE=cpu to use the CPU image.")
    return ["CUDAExecutionProvider", "CPUExecutionProvider"]


class ClipEmbedder:
    """Shared image/text CLIP space. Thread-safe; text embeddings are memoized."""

    def __init__(self, cache_dir: str | None = None, threads: int | None = None, model: str = "clip", device: str = "cpu"):
        from fastembed import ImageEmbedding, TextEmbedding

        vision, text = MODELS.get(model, MODELS["clip"])
        self.model = model
        self.device = device
        self.dimensions = 768 if model == "siglip2" else 512
        providers = execution_providers(device)
        self._img = ImageEmbedding(vision, cache_dir=cache_dir, threads=threads, providers=providers, cuda=False)
        self._txt = TextEmbedding(text, cache_dir=cache_dir, threads=threads, providers=providers, cuda=False)
        if device == "gpu":
            for tower in (self._img, self._txt):
                if "CUDAExecutionProvider" not in tower.model.model.get_providers():
                    raise RuntimeError("CUDA initialization failed; check NVIDIA drivers and the CUDA/cuDNN runtime. "
                                       "GPU mode cannot silently fall back to CPU.")
        self._lock = threading.Lock()
        self._text_cache: dict[str, np.ndarray] = {}

    def embed_images(self, images: list[Image.Image]) -> np.ndarray:
        if not images:
            return np.zeros((0, self.dimensions), dtype=np.float32)
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
        return np.vstack([self._text_cache[t] for t in texts]) if texts else np.zeros((0, self.dimensions), np.float32)


_singletons: dict[tuple[str, str, str | None], ClipEmbedder] = {}
ONNX_THREADS = min(8, os.cpu_count() or 4)
_singleton_lock = threading.Lock()


def get_clip_embedder(cache_dir: str | None = None, model: str = "clip", device: str = "cpu") -> ClipEmbedder:
    model = model if model in MODELS else "clip"
    key = (model, device, cache_dir)
    with _singleton_lock:
        if key not in _singletons:
            _singletons[key] = ClipEmbedder(cache_dir=cache_dir, threads=ONNX_THREADS, model=model, device=device)
        return _singletons[key]
