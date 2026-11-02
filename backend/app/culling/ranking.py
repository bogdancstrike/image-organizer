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

from app.culling.quality import Face, Quality, QualityRules, verdict

NEAR_DUPLICATE = 0.93  # cosine above which a candidate is "the same frame" as an existing pick


@dataclass
class PickInfo:
    score: float
    parts: dict[str, float] = field(default_factory=dict)  # 0..1 percentiles within the shoot
    reasons: list[str] = field(default_factory=list)
    profile: str = "general"


@dataclass
class Ranking:
    info: dict[str, PickInfo]
    labels: np.ndarray  # scene per id (same order as the ids passed to rank)


# ------------------------------------------------------------------ signals (raw, 0..1)
def relevant_faces(q: Quality, rules: QualityRules | None = None) -> list[Face]:
    if not q.faces:
        return []
    largest = max(f.area for f in q.faces)
    faces = [f for f in q.faces if f.area >= largest * .25]
    return [max(faces, key=lambda f: f.area)] if rules and rules.faces_rule == "main" else faces


def subject_focus(q: Quality, rules: QualityRules | None = None) -> float:
    faces = relevant_faces(q, rules)
    measured = [f for f in faces if f.landmarks_checked and f.sharpness is not None]
    scores = [f.sharpness for f in (measured or faces) if f.sharpness is not None]
    return .6 * min(scores) + .4 * sum(scores) / len(scores) if scores else q.sharpness


def technical(q: Quality, rules: QualityRules | None = None) -> float:
    sharp = min(1.0, max(0.0, (subject_focus(q, rules) - 0.3) / 0.5))
    sharp *= .85 + .15 * q.features.get("detail", 1.0)
    # Mean brightness alone cannot distinguish bad exposure from intentional low/high-key lighting.
    exposure = 1 - min(0.9, 0.55 * q.dark_clip + 0.9 * q.bright_clip)
    noise = 1 - min(1.0, q.noise / 0.09)
    return (0.60 * sharp + .05 * q.features.get("tenengrad", sharp) + 0.25 * exposure + 0.10 * noise) * (1 - .06*q.features.get("blocking", 0))


def face_expression(f: Face, profile: str = "portrait") -> float:
    e = f.expr or {}
    eyes = 1 - f.blink
    gaze = 1 - min(1.0, e.get("gaze", 0.0) * 1.4)
    smiling = f.smile > 0.45
    mouth = 1.0 if smiling else 1 - min(1.0, max(0.0, e.get("mouth", 0.0) - 0.2) * 1.6)  # open mouth is fine in a laugh
    frown = 1 - min(1.0, e.get("frown", 0.0) * 2.0)
    squint = 1.0 if smiling else 1 - min(1.0, max(0.0, e.get("squint", 0.0) - 0.4) * 1.5)
    yaw = 1 - min(1.0, max(0.0, e.get("yaw", 0.0) - 0.35) * 1.5)
    if profile == "fashion":
        # Editorial poses need not face the camera or smile.
        return 0.50 * eyes + 0.30 * mouth + 0.20 * frown
    return 0.32 * eyes + 0.18 * gaze + 0.14 * mouth + 0.10 * frown + 0.06 * squint + 0.10 * yaw + 0.10 * (0.5 + 0.5 * f.smile)


def expression(q: Quality, rules: QualityRules | None = None, profile: str = "portrait") -> float | None:
    if not q.faces:
        return None
    sizable = [f for f in relevant_faces(q, rules) if f.landmarks_checked]
    if not sizable:
        return None
    scores = [face_expression(f, profile) for f in sizable]
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


GENRES = {
    "portrait": "a close-up portrait photograph of a person",
    "fashion": "a fashion editorial photograph showing a model, clothes and a deliberate pose",
    "landscape": "a landscape photograph of mountains, forests, coast or a wide natural scene",
    "general": "a photograph of everyday objects, food, architecture or an event",
}
# Positive and negative prompts describe observable presentation, not bodies or personal worth.
PRESENTATION = {
    "portrait": ("a compelling expressive portrait with flattering light and subject separation", "an awkward portrait with distracting background and unflattering light"),
    "group": ("a well-timed group portrait with natural expressions", "an awkwardly timed group photo"),
    "fashion": ("an editorial fashion photograph with deliberate pose, readable garments and coherent styling", "a fashion snapshot with awkward framing, obscured clothing and distracting styling"),
    "landscape": ("a landscape photograph with depth, an interesting foreground and a clear focal point", "a flat landscape snapshot with no focal point or sense of depth"),
    "general": ("a compelling photograph with clear subject and storytelling", "a cluttered accidental snapshot with no clear subject"),
}
WEIGHTS = {
    "portrait": {"tech": .28, "expr": .26, "comp": .14, "light": .14, "aes": .18},
    "group": {"tech": .30, "expr": .34, "comp": .10, "light": .12, "aes": .14},
    "fashion": {"tech": .25, "expr": .10, "comp": .20, "light": .20, "aes": .25},
    "landscape": {"tech": .34, "expr": 0, "comp": .24, "light": .18, "aes": .24},
    "general": {"tech": .40, "expr": 0, "comp": .18, "light": .18, "aes": .24},
}


def _semantic(E: np.ndarray, embedder):
    pairs = list(PRESENTATION.values()) + [
        ("a photograph with intentional beautiful lighting and retained highlight detail", "a photograph with harsh flat light and blown highlights"),
        ("a photograph with balanced composition, depth and a clear focal point", "a cluttered badly framed photograph with distracting composition"),
    ]
    prompts = list(GENRES.values()) + [t for pair in pairs for t in pair]
    T = np.asarray(embedder.embed_texts(prompts), dtype=np.float32)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    genre_logits = 20 * E @ T[:len(GENRES)].T
    genre_logits -= genre_logits.max(axis=1, keepdims=True)
    probs = np.exp(genre_logits); probs /= probs.sum(axis=1, keepdims=True)
    paired = (E @ T[len(GENRES):].T).reshape(len(E), len(pairs), 2)
    signals = 1 / (1 + np.exp(-np.clip(20 * (paired[:, :, 0] - paired[:, :, 1]), -30, 30)))
    return probs, signals


def rank(ids: list[str], quality: dict[str, Quality], E: np.ndarray, embedder, rules: QualityRules,
         profile: str = "auto", options: dict | None = None) -> Ranking:
    """Explainable recommendations: absolute quality + shoot/scene comparisons, adapted to genre."""
    if profile not in ("auto", *GENRES):
        raise ValueError("Unknown culling profile")
    n = len(ids)
    if n == 0:
        return Ranking({}, np.zeros(0, dtype=int))
    E = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
    try:
        probabilities, semantic = _semantic(E, embedder)
    except Exception:  # a missing text tower leaves semantic scores neutral
        probabilities = np.full((n, len(GENRES)), 1 / len(GENRES))
        semantic = np.full((n, len(PRESENTATION) + 2), .5)
    profiles = []
    for i, fid in enumerate(ids):
        q = quality[fid]
        chosen = profile
        if chosen == "auto":
            winner = int(probabilities[i].argmax())
            chosen = list(GENRES)[winner] if probabilities[i, winner] >= .45 else ("portrait" if q.faces else "general")
            if q.faces and chosen in ("portrait", "general"):
                largest = max(f.area for f in q.faces)
                if sum(f.area >= largest * .25 for f in q.faces) > 1 and rules.faces_rule != "main":
                    chosen = "group"
        profiles.append(chosen)
    raw = {k: np.zeros(n) for k in ("tech", "expr", "comp", "light", "aes")}
    absolute = np.zeros(n)
    for i, fid in enumerate(ids):
        q, kind = quality[fid], profiles[i]
        expr = expression(q, rules, kind)
        raw["tech"][i] = technical(q, rules)
        raw["expr"][i] = .5 if expr is None else expr
        geometry = composition(q)
        balance = q.features.get("balance", geometry)
        separation = q.features.get("separation", .5)
        raw["comp"][i] = .30 * geometry + .40 * semantic[i, -1] + .20 * balance + .10 * separation
        raw["light"][i] = semantic[i, -2]
        raw["aes"][i] = semantic[i, list(PRESENTATION).index(kind)]
        weights = dict(WEIGHTS[kind])
        if expr is None:
            weights["expr"] = 0
        absolute[i] = sum(weights[k] * raw[k][i] for k in weights) / sum(weights.values())
    options = options or {}
    relevance = None
    if options.get("subject_prompt", "").strip():
        try:
            T = np.asarray(embedder.embed_texts([options["subject_prompt"].strip(), "a photograph"]), dtype=np.float32)
            T /= np.linalg.norm(T, axis=1, keepdims=True)+1e-9
            logits = E @ T.T
            relevance = 1/(1+np.exp(-np.clip(20*(logits[:,0]-logits[:,1]),-30,30)))
            absolute = .9*absolute+.1*relevance
        except (RuntimeError, ValueError, OSError):
            pass
    social = {}
    if options.get("social_media"):
        from app.culling.social import assess
        social = assess(ids, quality, E, embedder, options.get("social_format", "portrait"))
        weight = float(options.get("social_weight", .25))
        absolute = (1-weight)*absolute + weight*np.array([social[fid]["social"] for fid in ids])
    labels = scenes(E)
    novelty = np.zeros(n)
    frontier = np.zeros(n)
    vectors = np.column_stack([raw[k] for k in ("tech", "expr", "comp", "light", "aes")])
    for lab in np.unique(labels):
        group = np.where(labels == lab)[0]
        # Bounded chunks avoid allocating the full similarity/dominance matrix for large shoots.
        for start in range(0, len(group), 128):
            positions = group[start:start+128]
            similarities = E[positions] @ E[group].T
            similarities[np.arange(len(positions)), np.arange(start,start+len(positions))] = -1
            novelty[positions] = np.clip((1-similarities.max(axis=1))/.3, 0, 1)
            other = vectors[group][None, :, :]; current = vectors[positions][:, None, :]
            frontier[positions] = ~np.any(np.all(other >= current, axis=2) & np.any(other > current+.01, axis=2), axis=1)
    if options.get("preserve_unique", True):
        absolute = .97*absolute + .03*novelty
    global_rank = _pct(absolute)
    local_rank = global_rank.copy()
    for lab in np.unique(labels):
        idx = np.where(labels == lab)[0]
        if len(idx) >= 3:
            local_rank[idx] = _pct(absolute[idx])
    out = {}
    for i, fid in enumerate(ids):
        q, kind = quality[fid], profiles[i]
        value = .80 * absolute[i] + .10 * global_rank[i] + .10 * local_rank[i]
        # Relative winners in a technically poor shoot must not become top picks.
        value *= min(1.0, max(.05, (subject_focus(q, rules) - .10) / .40))
        rejected = verdict(q, rules)[0]
        if rejected:
            value = min(.24, value * .3)
        parts = {k: round(float(v[i]), 3) for k, v in raw.items()}
        if not any(f.landmarks_checked for f in relevant_faces(q, rules)) or WEIGHTS[kind]["expr"] == 0:
            parts.pop("expr")
        parts.update({key: q.features[key] for key in ("detail", "balance", "separation", "tenengrad", "directionality", "blocking", "thumbnail") if key in q.features})
        parts.update(social.get(fid, {}))
        if relevance is not None:
            parts["relevance"] = round(float(relevance[i]),3)
        parts["novelty"] = round(float(novelty[i]), 3)
        parts["pareto"] = float(frontier[i]) if options.get("pareto_review", True) else 0.
        parts["relative"] = round(float(global_rank[i]), 3)
        reasons = []
        if social and social[fid].get("aesthetic", 0) >= .65:
            reasons.append("strong learned visual appeal (LAION)")
        if social and social[fid]["crop"] < .65:
            reasons.append("proposed social crop may cut important content")
        if social and social[fid]["clarity"] >= .75:
            reasons.append("clear at thumbnail size")
        if frontier[i] and options.get("pareto_review", True):
            reasons.append("alternative strengths in its scene")
        if novelty[i] >= .8:
            reasons.append("distinct view in its scene")
        if parts["tech"] >= .80:
            reasons.append("sharp eyes" if q.faces else "clear detail")
        if kind in ("portrait", "group") and parts.get("expr", 0) >= .8:
            reasons.append("strong group expressions" if kind == "group" else "natural expression")
        if parts["light"] >= .65:
            reasons.append("intentional light")
        if parts["comp"] >= .70:
            reasons.append("balanced composition")
        if parts["aes"] >= .65:
            reasons.append({"fashion": "pose & styling", "landscape": "depth & focal point"}.get(kind, "strong presentation"))
        if (labels == labels[i]).sum() >= 3 and local_rank[i] >= .99 and not rejected:
            reasons.insert(0, "best of its scene")
        if rejected:
            reasons.insert(0, "check: " + rejected)
        if not reasons:
            reasons.append("balanced quality" if value >= .5 else "review technical quality")
        out[fid] = PickInfo(round(float(np.clip(value, 0, 1)), 4), parts, reasons[:4], kind)
    return Ranking(out, labels)


def select(ids: list[str], ranking: Ranking, E: np.ndarray, n_picks: int, min_score: float = .5) -> list[str]:
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
        if info[fid].score < min_score:
            return False
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
