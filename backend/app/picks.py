"""Picks: the strongest frames of a shoot, the way a photographer culls.

What makes a pick (each signal is ranked *within this shoot*, and again within its scene, so a pick is the best
version of each moment rather than simply the sharpest file):

- Technical: focus on the eyes (or the sharpest region without faces), exposure, noise.
- Expression (per face, worst face counts most in group shots): eyes open, looking at the camera, mouth not caught
  mid-word, no frown/squint, head not turned away, a little smile bonus.
- Composition: main subject near a rule-of-thirds point, headroom, face not cut by the frame, level horizon.
- Aesthetics: zero-shot CLIP/SigLIP judgement ("stunning editorial photo, flattering light" vs. "amateur snapshot").
- Story: picks are spread across scenes (in proportion to scene size) and near-duplicates of a pick are skipped.

Every pick carries short reasons ("sharp eyes", "best of its scene", …) so the choice is explainable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .quality import Face, Quality, QualityRules, verdict

AES_POS = [
    "a stunning professional photograph", "an award-winning portrait with beautiful light",
    "a magazine-quality editorial photo", "a beautifully composed photo with depth and mood",
    "a flattering photo of a person looking their best", "an emotional, story-telling moment",
]
AES_NEG = [
    "a blurry amateur snapshot", "a badly composed, cluttered photo", "an unflattering photo with an awkward expression",
    "a dull, flat, poorly lit photo", "an accidental photo of nothing", "a photo with the subject cut off",
]
NEAR_DUPLICATE = 0.93  # cosine above which a candidate is "the same frame" as an existing pick


@dataclass
class PickInfo:
    score: float
    parts: dict[str, float] = field(default_factory=dict)  # 0..1 percentiles within the shoot
    reasons: list[str] = field(default_factory=list)


@dataclass
class Ranking:
    info: dict[str, PickInfo]
    labels: np.ndarray  # scene per id (same order as the ids passed to rank)


# ------------------------------------------------------------------ signals (raw, 0..1)
def technical(q: Quality) -> float:
    sharp = min(1.0, max(0.0, (q.sharpness - 0.3) / 0.5))
    exposure = (1 - min(1.0, abs(q.brightness - 0.45) / 0.45)) * (1 - min(0.5, q.dark_clip + q.bright_clip))
    noise = 1 - min(1.0, q.noise / 0.08)
    return 0.65 * sharp + 0.25 * exposure + 0.10 * noise


def face_expression(f: Face) -> float:
    e = f.expr or {}
    eyes = 1 - f.blink
    gaze = 1 - min(1.0, e.get("gaze", 0.0) * 1.4)
    smiling = f.smile > 0.45
    mouth = 1.0 if smiling else 1 - min(1.0, max(0.0, e.get("mouth", 0.0) - 0.2) * 1.6)  # open mouth is fine in a laugh
    frown = 1 - min(1.0, e.get("frown", 0.0) * 2.0)
    squint = 1.0 if smiling else 1 - min(1.0, max(0.0, e.get("squint", 0.0) - 0.4) * 1.5)
    yaw = 1 - min(1.0, max(0.0, e.get("yaw", 0.0) - 0.35) * 1.5)
    return 0.32 * eyes + 0.18 * gaze + 0.14 * mouth + 0.10 * frown + 0.06 * squint + 0.10 * yaw + 0.10 * (0.5 + 0.5 * f.smile)


def expression(q: Quality) -> float | None:
    if not q.faces:
        return None
    biggest = max(f.area for f in q.faces)
    sizable = [f for f in q.faces if f.area >= biggest * 0.25] or q.faces
    scores = [face_expression(f) for f in sizable]
    return 0.6 * min(scores) + 0.4 * (sum(scores) / len(scores))  # one blink spoils a group shot


def composition(q: Quality) -> float:
    s = 0.7
    if q.faces:
        f = max(q.faces, key=lambda x: x.area)
        x0, y0, x1, y1 = f.box
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        near = min(math.hypot(cx - tx, cy - ty) for tx in (1 / 3, 1 / 2, 2 / 3) for ty in (1 / 3, 0.42))
        s = 1 - min(1.0, near / 0.35)
        if y0 < 0.02 and f.area < 0.25:  # head touching the top edge
            s -= 0.25
        if x0 < 0.005 or x1 > 0.995:  # face cut by a side
            s -= 0.35
    if q.tilt is not None and 1.5 <= abs(q.tilt) <= 8:
        s -= min(0.3, abs(q.tilt) / 20)
    return max(0.0, min(1.0, s))


def aesthetic(E: np.ndarray, embedder) -> np.ndarray:
    def enc(prompts):
        v = np.asarray(embedder.embed_texts(prompts), dtype=np.float32)
        return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)

    return (E @ enc(AES_POS).T).mean(axis=1) - (E @ enc(AES_NEG).T).mean(axis=1)


# ------------------------------------------------------------------ ranking
def _pct(values: np.ndarray) -> np.ndarray:
    """Percentile rank 0..1 (ties averaged); a single value is 0.5."""
    n = len(values)
    if n == 1:
        return np.array([0.5])
    order = values.argsort(kind="stable")
    ranks = np.empty(n)
    ranks[order] = np.arange(n)
    for v in np.unique(values):
        idx = values == v
        if idx.sum() > 1:
            ranks[idx] = ranks[idx].mean()
    return ranks / (n - 1)


def scenes(E: np.ndarray) -> np.ndarray:
    """Scene labels (the moments of a shoot) from normalized embeddings."""
    n = len(E)
    if n < 6:
        return np.zeros(n, dtype=int)
    if n <= 2500:
        from sklearn.cluster import AgglomerativeClustering

        return AgglomerativeClustering(n_clusters=None, distance_threshold=0.3, metric="cosine", linkage="average").fit_predict(E)
    from sklearn.cluster import KMeans

    return KMeans(n_clusters=min(80, n // 25), n_init=2, random_state=0).fit_predict(E)


def rank(ids: list[str], quality: dict[str, Quality], E: np.ndarray, embedder, rules: QualityRules) -> Ranking:
    """Score every frame 0..1 relative to the shoot and to its scene."""
    n = len(ids)
    if n == 0:
        return Ranking({}, np.zeros(0, dtype=int))
    E = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
    tech = np.array([technical(quality[i]) for i in ids])
    expr_raw = [expression(quality[i]) for i in ids]
    has_face = np.array([x is not None for x in expr_raw])
    expr = np.array([x if x is not None else 0.0 for x in expr_raw])
    comp = np.array([composition(quality[i]) for i in ids])
    try:
        aes = aesthetic(E, embedder)
    except Exception:  # noqa: BLE001 - no text tower: aesthetics stay neutral
        aes = np.zeros(n)
    P = {"tech": _pct(tech), "comp": _pct(comp), "aes": _pct(aes), "expr": np.full(n, 0.5)}
    if has_face.any():
        P["expr"][has_face] = _pct(expr[has_face])
    labels = scenes(E)

    def blend(i: int) -> float:
        if has_face[i]:
            return 0.28 * P["tech"][i] + 0.30 * P["expr"][i] + 0.14 * P["comp"][i] + 0.28 * P["aes"][i]
        return 0.40 * P["tech"][i] + 0.18 * P["comp"][i] + 0.42 * P["aes"][i]

    glob = np.array([blend(i) for i in range(n)])
    local = glob.copy()
    for lab in np.unique(labels):
        idx = np.where(labels == lab)[0]
        if len(idx) >= 3:
            local[idx] = _pct(glob[idx])
    out: dict[str, PickInfo] = {}
    for i, fid in enumerate(ids):
        q = quality[fid]
        s = 0.6 * glob[i] + 0.4 * local[i]
        if verdict(q, rules)[0]:  # blurry, eyes closed, … can't be a pick
            s *= 0.3
        if has_face[i] and max(f.blink for f in q.faces) > 0.5:
            s *= 0.5
        parts = {k: round(float(v[i]), 3) for k, v in P.items()}
        reasons = []
        if parts["tech"] >= 0.8:
            reasons.append("sharp eyes" if has_face[i] else "tack-sharp")
        if has_face[i] and parts["expr"] >= 0.8:
            reasons.append("great expression")
        if parts["aes"] >= 0.8:
            reasons.append("beautiful light & mood")
        if parts["comp"] >= 0.85:
            reasons.append("strong composition")
        if (labels == labels[i]).sum() >= 3 and local[i] >= 0.99:
            reasons.insert(0, "best of its scene")
        out[fid] = PickInfo(round(float(s), 4), parts, reasons[:3])
    return Ranking(out, labels)


def select(ids: list[str], ranking: Ranking, E: np.ndarray, n_picks: int) -> list[str]:
    """Best frames, spread across scenes, without near-duplicates of an existing pick."""
    if n_picks <= 0 or not ids:
        return []
    info, labels = ranking.info, ranking.labels
    if len(labels) != len(ids):
        labels = np.zeros(len(ids), dtype=int)
    E = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
    pos = {fid: i for i, fid in enumerate(ids)}
    sizes = {int(lab): int((labels == lab).sum()) for lab in np.unique(labels)}
    quota = {lab: max(1, math.ceil(n_picks * size / len(ids))) for lab, size in sizes.items()}
    taken: dict[int, int] = {}
    order = sorted(ids, key=lambda f: -info[f].score)
    median = float(np.median([info[f].score for f in ids]))
    chosen: list[str] = []

    def ok(fid: str, respect_quota: bool) -> bool:
        lab = int(labels[pos[fid]])
        if respect_quota and taken.get(lab, 0) >= quota[lab]:
            return False
        if chosen and float((E[[pos[c] for c in chosen]] @ E[pos[fid]]).max()) >= NEAR_DUPLICATE:
            return False
        return True

    def take(fid: str) -> None:
        chosen.append(fid)
        lab = int(labels[pos[fid]])
        taken[lab] = taken.get(lab, 0) + 1

    # 1) the story: every sizeable scene gets its best frame (when it is a decent frame)
    for lab, size in sorted(sizes.items(), key=lambda kv: -kv[1]):
        if len(chosen) >= n_picks or size < 3:
            continue
        best = next((f for f in order if int(labels[pos[f]]) == lab), None)
        if best and info[best].score >= median and ok(best, True):
            take(best)
    # 2) the strongest remaining frames: within scene quotas first, then freely
    for respect in (True, False):
        for f in order:
            if len(chosen) >= n_picks:
                break
            if f not in chosen and ok(f, respect):
                take(f)
    return chosen
