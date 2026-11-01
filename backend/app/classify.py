"""Categorization strategies: zero-shot, auto-discovery, by date (REQ-CAT-3..6)."""
from __future__ import annotations

import calendar
from datetime import datetime

import numpy as np

from .embedder import Embedder, normalize
from .presets import FACETS, THEMES, VOCABULARY

LOGIT_SCALE = 100.0
STRICT_SCREENSHOT = 0.6


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


def media_mask(categories: list[dict], kinds: list[str]) -> np.ndarray:
    """(n_files, n_cats) bool: which folders accept each file.

    If a set has folders dedicated to a kind (media == "video"), files of that kind go ONLY there;
    otherwise they use the "any" folders. Folders dedicated to the other kind are never used.
    """
    media = np.array([c.get("media") or "any" for c in categories])
    mask = np.ones((len(kinds), len(categories)), dtype=bool)
    for kind in ("image", "video"):
        dedicated = media == kind
        allowed = dedicated if dedicated.any() else media == "any"
        rows = [i for i, k in enumerate(kinds) if k == kind]
        if rows and allowed.any():
            mask[rows] = allowed
    return mask


def classify_with_set(
    embs: np.ndarray,
    screenshot_flags: list[bool],
    categories: list[dict],
    embedder: Embedder,
    min_confidence: float,
    kinds: list[str] | None = None,
) -> list[tuple[str | None, float, str]]:
    """Preset/custom strategy. Returns (category_id or None for Unsorted, confidence, source)."""
    cat_mat = category_matrix(embedder, categories)
    shot_id = screenshot_category(categories)
    out: list[tuple[str | None, float, str]] = []
    if len(embs) == 0:
        return out
    logits = LOGIT_SCALE * (embs @ cat_mat.T)
    if kinds is not None:
        logits = np.where(media_mask(categories, kinds), logits, -np.inf)
    probs = softmax(logits)
    # per-category floor: CLIP alone must be very sure about "Screenshots" (the rule handles real ones)
    floors = np.array([
        max(min_confidence, float(c.get("min_confidence") or (STRICT_SCREENSHOT if c["id"] == shot_id else 0)))
        for c in categories
    ])
    for i in range(len(embs)):
        if shot_id and screenshot_flags[i] and np.isfinite(logits[i, [c["id"] for c in categories].index(shot_id)]):
            out.append((shot_id, 1.0, "rule"))
            continue
        chosen = None
        for j in np.argsort(-probs[i])[:2]:  # best, else runner-up
            if probs[i, j] >= floors[j]:
                chosen = int(j)
                break
        if chosen is None:
            out.append((None, float(probs[i].max()), "clip"))
        else:
            out.append((categories[chosen]["id"], float(probs[i, chosen]), "clip"))
    return out


def choose_k(embs: np.ndarray, max_k: int, seed: int = 0, bias: float = 0.002) -> tuple[np.ndarray, np.ndarray]:
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
        score += bias * k
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


# ------------------------------------------------------------ context-aware auto discovery
def facet_bank(embedder: Embedder, facets: list[str]) -> tuple[list[str], np.ndarray, list[str]]:
    labels, prompts, facet_of = [], [], []
    for f in facets:
        for label, prompt in FACETS[f]:
            labels.append(label)
            prompts.append(prompt)
            facet_of.append(f)
    return labels, embedder.embed_texts(prompts), facet_of


def facet_features(embs: np.ndarray, bank: np.ndarray) -> np.ndarray:
    """z-scored similarity of each photo to each prompt: 'how much more X than the rest of this folder'."""
    s = embs @ bank.T
    return (s - s.mean(axis=0)) / (s.std(axis=0) + 1e-6)


def describe_clusters(z: np.ndarray, labels: np.ndarray, n: int, names: list[str], facet_of: list[str]) -> list[list[str]]:
    """Name candidates per cluster, best first: what makes the group stand out, from up to two facets."""
    out = []
    for c in range(n):
        members = labels == c
        if not members.any():
            out.append([f"Group {c + 1}"])
            continue
        m = z[members].mean(axis=0)
        order = [int(i) for i in np.argsort(-m)]
        top, seen = [], set()
        for i in order:
            if facet_of[i] not in seen:
                top.append(i)
                seen.add(facet_of[i])
            if len(top) == 3:
                break
        cands = []
        if len(top) >= 2:
            cands.append(f"{names[top[0]]} · {names[top[1]]}")
        cands.append(names[top[0]])
        if len(top) >= 3:
            cands.append(f"{names[top[0]]} · {names[top[2]]}")
            cands.append(f"{names[top[1]]} · {names[top[2]]}")
        cands += [f"{names[i]}" for i in order[1:6]]
        out.append(cands)
    return out


def unique_names(candidates: list[list[str]]) -> list[str]:
    used: set[str] = set()
    result = []
    for i, cands in enumerate(candidates):
        pick = next((c for c in cands if c.lower() not in used), f"{cands[0]} {i + 1}")
        used.add(pick.lower())
        result.append(pick)
    return result


def collection_theme(embs: np.ndarray, embedder: Embedder) -> tuple[str, float]:
    """What kind of collection the whole folder is (e.g. 'Trash the dress'), with a softmax confidence."""
    if len(embs) == 0:
        return "", 0.0
    mean = normalize(embs.mean(axis=0))
    t = embedder.embed_texts([p for _, p in THEMES])
    probs = softmax(LOGIT_SCALE * (mean[None, :] @ t.T))[0]
    i = int(probs.argmax())
    return THEMES[i][0], float(probs[i])
