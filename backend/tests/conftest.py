"""Shared fixtures. Tests use a deterministic FakeEmbedder (color space) instead of CLIP."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.infrastructure.config import Settings
from app.infrastructure.embeddings import normalize

COLORS = {"red": (220, 30, 30), "green": (30, 180, 40), "blue": (30, 60, 220)}


class FakeEmbedder:
    """Images embed to their mean RGB (+ a constant), texts by color keyword."""

    def __init__(self):
        self.image_calls = 0

    def embed_images(self, images):
        self.image_calls += len(images)
        rows = []
        for im in images:
            arr = np.asarray(im.convert("RGB").resize((8, 8)), dtype=np.float32).mean(axis=(0, 1)) / 255.0
            rows.append(np.concatenate([arr, [0.05]]))
        return normalize(np.array(rows))

    def embed_texts(self, texts):
        rows = []
        for t in texts:
            t = t.lower()
            v = np.array([0.0, 0.0, 0.0, 0.05])
            if "red" in t:
                v[0] = 1
            if "green" in t:
                v[1] = 1
            if "blue" in t:
                v[2] = 1
            if not v[:3].any():
                v[:3] = 0.33
            rows.append(v)
        return normalize(np.array(rows))


def make_image(path: Path, color, size=(320, 240), fmt=None, noise_seed: int | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    arr = np.zeros((size[1], size[0], 3), np.uint8)
    arr[:] = color
    # add structure so pHash differs between unrelated images
    rng = np.random.default_rng(noise_seed if noise_seed is not None else abs(hash(path.name)) % 2**32)
    for _ in range(6):
        x, y = rng.integers(0, size[0] - 40), rng.integers(0, size[1] - 40)
        arr[y : y + 40, x : x + 40] = rng.integers(0, 255, 3)
    Image.fromarray(arr).save(path, fmt)
    return path


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    lib = tmp_path / "library"
    lib.mkdir()
    return Settings(
        library_root=lib.resolve(),
        data_dir=tmp_path / "data",
        model_dir=None,
        openai_api_key=None,
        openai_model="gpt-6-luna",
        reasoning_effort="low",
        workers=4,
        output_dir_name="Organized",
        static_dir=None,
    )


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


HAS_FFMPEG = shutil.which("ffmpeg") is not None


def make_video(path: Path, color: str = "red", seconds: float = 1.5) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=160x120:d={seconds}",
         "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )
    return path
