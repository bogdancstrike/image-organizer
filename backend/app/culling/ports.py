"""Face-analysis port; scoring does not load or configure detection models."""
from __future__ import annotations
from typing import Protocol, TYPE_CHECKING
import numpy as np
if TYPE_CHECKING:
    from app.culling.quality import Face

class FaceDetector(Protocol):
    available: bool
    def detect(self, rgb: np.ndarray) -> list[Face]: ...
