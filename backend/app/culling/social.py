"""Posting-readiness heuristics inspired by research; no engagement or memorability prediction."""
from __future__ import annotations

import math
import numpy as np

FORMATS = {"portrait": 4 / 5, "square": 1.0, "vertical": 9 / 16, "landscape": 16 / 9}
PAIRS = [
    ("a photograph with a clear distinctive subject recognizable at thumbnail size", "a confusing cluttered photograph with no clear subject"),
    ("a photograph capturing an expressive engaging moment or a distinctive visual story", "an uneventful repetitive photograph with no meaningful focal point"),
]


def crop_fit(q, format: str) -> float:
    """Central-crop retained area and important face retention. Evaluates a crop; never edits a photo."""
    if format == "original":
        return 1.0
    target = FORMATS[format]
    aspect = q.features.get("aspect_ratio", target)
    cw, ch = (min(1., target / aspect), min(1., aspect / target))
    x0, y0 = (1 - cw) / 2, (1 - ch) / 2
    retained = []
    for face in q.faces:
        if face.area < max(f.area for f in q.faces) * .25:
            continue
        a, b, c, d = face.box
        intersection = max(0., min(c, x0+cw)-max(a, x0)) * max(0., min(d, y0+ch)-max(b, y0))
        retained.append(intersection / max(1e-9, (c-a)*(d-b)))
    area = math.sqrt(cw * ch)
    return float(area * (.25 + .75 * min(retained))) if retained else float(area)


def assess(ids, quality, E, embedder, format="portrait") -> dict[str, dict[str, float]]:
    if format not in (*FORMATS, "original"):
        raise ValueError("unknown social crop format")
    if not ids:
        return {}
    semantic = np.full((len(ids), 2), .5)
    try:
        T = np.asarray(embedder.embed_texts([p for pair in PAIRS for p in pair]), dtype=np.float32)
        T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
        X = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
        values = (X @ T.T).reshape(len(ids), 2, 2)
        semantic = 1 / (1 + np.exp(-np.clip(20 * (values[:, :, 0]-values[:, :, 1]), -30, 30)))
    except (RuntimeError, ValueError, OSError):
        pass
    out = {}
    for i, fid in enumerate(ids):
        q = quality[fid]; f = q.features
        parts = {"crop": crop_fit(q, format), "clarity": .55*f.get("thumbnail", .5)+.45*float(semantic[i, 0]),
                 "impact": float(semantic[i, 1]), "contrast": f.get("contrast", .5), "color": f.get("color", .5)}
        # Color is a weak cue: monochrome, restrained grading and skin tones need not be highly saturated.
        score = .30*parts["clarity"]+.25*parts["crop"]+.25*parts["impact"]+.15*parts["contrast"]+.05*parts["color"]
        if "aesthetic" in f:
            parts["aesthetic"] = f["aesthetic"]
            score = .7 * score + .3 * parts["aesthetic"]
        score *= .85+.15*f.get("resolution", 1.)
        out[fid] = {**{k: round(v, 3) for k, v in parts.items()}, "social": round(float(score), 3)}
    return out
