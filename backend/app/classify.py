"""Categorization strategies: zero-shot, auto-discovery, by date (REQ-CAT-3..6)."""
from __future__ import annotations

import calendar
from datetime import datetime

import numpy as np

from .embedder import Embedder, normalize
from .presets import VOCABULARY

LOGIT_SCALE = 100.0


def category_matrix(embedder: Embedder, categories: list[dict]) -> np.ndarray:
    """One normalized text vector per category = mean of its prompt embeddings."""
    rows = []
    for c in categories:
        prompts = c.get("prompts") or [f"a photo of {c['name']}"]
        rows.append(normalize(embedder.embed_texts(prompts).mean(axis=0)))
    return np.vstack(rows)


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - x.max(axis=1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=1, keepdims=True)


def zero_shot(embs: np.ndarray, cat_mat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (best category index, probability) for each embedding."""
    if len(embs) == 0:
        return np.zeros(0, int), np.zeros(0)
    probs = softmax(LOGIT_SCALE * (embs @ cat_mat.T))
    idx = probs.argmax(axis=1)
    return idx, probs[np.arange(len(idx)), idx]


def screenshot_category(categories: list[dict]) -> str | None:
    for c in categories:
        if "screenshot" in c["id"].lower() or "screenshot" in c["name"].lower():
            return c["id"]
    return None


def classify_with_set(
    embs: np.ndarray,
    screenshot_flags: list[bool],
    categories: list[dict],
    embedder: Embedder,
    min_confidence: float,
) -> list[tuple[str | None, float, str]]:
    """Preset/custom strategy. Returns (category_id or None for Unsorted, confidence, source)."""
    cat_mat = category_matrix(embedder, categories)
    idx, prob = zero_shot(embs, cat_mat)
    shot_id = screenshot_category(categories)
    out: list[tuple[str | None, float, str]] = []
    for i in range(len(idx)):
        if shot_id and screenshot_flags[i]:
            out.append((shot_id, 1.0, "rule"))
        elif prob[i] >= min_confidence:
            out.append((categories[int(idx[i])]["id"], float(prob[i]), "clip"))
        else:
            out.append((None, float(prob[i]), "clip"))
    return out


def choose_k(embs: np.ndarray, max_k: int, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """KMeans with k chosen by silhouette. Returns (labels, normalized centroids)."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    n = len(embs)
    if n < 6:
        return np.zeros(n, int), normalize(embs.mean(axis=0, keepdims=True))
    upper = max(2, min(max_k, n // 3))
    best = None
    for k in range(2, upper + 1):
        km = KMeans(n_clusters=k, n_init=3, random_state=seed).fit(embs)
        if len(set(km.labels_)) < 2:
            continue
        score = silhouette_score(embs, km.labels_, metric="cosine", sample_size=min(n, 2000), random_state=seed)
        # Small bias toward more folders: users prefer finer sorting
        score += 0.002 * k
        if best is None or score > best[0]:
            best = (score, km)
    if best is None:
        return np.zeros(n, int), normalize(embs.mean(axis=0, keepdims=True))
    km = best[1]
    return km.labels_.astype(int), normalize(km.cluster_centers_)


def name_by_vocabulary(centroids: np.ndarray, embedder: Embedder) -> list[tuple[str, str]]:
    """Name clusters by the best still-unused vocabulary label (REQ-CAT-5 fallback)."""
    labels = [v[0] for v in VOCABULARY]
    vocab = embedder.embed_texts([f"a photo of {l.lower()}" for l in labels])
    sims = centroids @ vocab.T
    used: set[int] = set()
    names = []
    # assign most confident clusters first
    order = np.argsort(-sims.max(axis=1))
    result: dict[int, tuple[str, str]] = {}
    for ci in order:
        for vi in np.argsort(-sims[ci]):
            if int(vi) not in used:
                used.add(int(vi))
                result[int(ci)] = VOCABULARY[int(vi)]
                break
    for ci in range(len(centroids)):
        names.append(result.get(ci, (f"Group {ci + 1}", "📁")))
    return names


def representatives(embs: np.ndarray, labels: np.ndarray, centroids: np.ndarray, per: int = 6) -> list[list[int]]:
    reps = []
    for c in range(len(centroids)):
        members = np.where(labels == c)[0]
        if len(members) == 0:
            reps.append([])
            continue
        sims = embs[members] @ centroids[c]
        reps.append([int(members[i]) for i in np.argsort(-sims)[:per]])
    return reps


def date_category(ts: float, granularity: str = "month") -> str:
    d = datetime.fromtimestamp(ts)
    if granularity == "year":
        return f"{d.year}"
    if granularity == "day":
        return f"{d.year}/{d.month:02d}/{d.year}-{d.month:02d}-{d.day:02d}"
    return f"{d.year}/{d.month:02d} - {calendar.month_name[d.month]}"
