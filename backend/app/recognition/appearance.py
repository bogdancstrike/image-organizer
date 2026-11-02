"""Shoot-local appearance matching. Face-confirmed examples remain the only training labels.

Whole-image embeddings carry clothing, hair, silhouette and body-detail context. A balanced
linear classifier and a multi-view neighbour gallery must agree; filename sequence evidence
can support a difficult match but never assign an identity on its own. Scores are heuristic,
not calibrated identity probabilities. Nothing is learned across unrelated folders.
"""
from __future__ import annotations

from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath
import re

import numpy as np

from app.recognition.ports import normalize


@dataclass
class AppearanceMatch:
    person: int = -1
    similarity: float = 0.0
    evidence: tuple[str, ...] = ()


def sequence_hints(paths: list[str], labels: np.ndarray, max_gap: int = 20) -> list[int]:
    """Only use bracketing face anchors from the same directory/camera filename series."""
    keys = []
    series: dict[tuple, dict[int, set[int]]] = {}
    for path, label in zip(paths, labels):
        p = PurePosixPath(path)
        match = re.fullmatch(r"(.*?)(\d{3,})(?:[-_]\d+)?", p.stem)
        key = (str(p.parent), match[1].lower()) if match else None
        number = int(match[2]) if match else -1
        keys.append((key, number))
        if key is not None and label >= 0:
            series.setdefault(key, {}).setdefault(number, set()).add(int(label))
    ordered = {key: sorted(values) for key, values in series.items()}
    out = []
    for key, number in keys:
        numbers = ordered.get(key, [])
        pos = bisect_left(numbers, number)
        value = -1
        if 0 < pos < len(numbers):
            before, after = numbers[pos - 1], numbers[pos]
            left, right = series[key][before], series[key][after]
            if number != after and number - before <= max_gap and after - number <= max_gap and left == right and len(left) == 1:
                value = next(iter(left))
        out.append(value)
    return out


def match_appearances(embeddings: np.ndarray, labels: np.ndarray, paths: list[str],
                      candidates: list[int]) -> list[AppearanceMatch]:
    """Match candidate rows to known people, retaining outliers and conflicting evidence."""
    anchors = np.flatnonzero(labels >= 0)
    if not candidates or len(anchors) < 2:
        return [AppearanceMatch() for _ in candidates]
    from sklearn.linear_model import LogisticRegression
    from threadpoolctl import threadpool_limits

    E = normalize(embeddings)
    C = normalize(E - E.mean(axis=0, keepdims=True))
    # Keep original content alongside shoot-centered detail, so centering cannot erase the subject.
    features = normalize(np.hstack([E, .6 * C]))
    classes = np.unique(labels[anchors])
    probabilities = None
    if len(classes) > 1 and len(anchors) >= 6:
        with threadpool_limits(limits=2):
            model = LogisticRegression(C=15, class_weight="balanced", max_iter=500)
            model.fit(features[anchors], labels[anchors])
            probabilities = model.predict_proba(features[candidates])
            classes = model.classes_
    hints = sequence_hints(paths, labels)
    similarities = C[candidates] @ C[anchors].T
    raw = E[candidates] @ E[anchors].T
    results = []
    for offset, row in enumerate(candidates):
        sim = similarities[offset]
        nearest = np.argsort(-sim)[:min(5, len(anchors))]
        votes = Counter(int(labels[anchors[i]]) for i in nearest)
        neighbour, count = votes.most_common(1)[0]
        best_sim = float(sim[nearest[0]])
        # A classifier always chooses a class, even for strangers. Require real local similarity too.
        supported = best_sim >= .28 and float(raw[offset, nearest[0]]) >= .45
        person, evidence = -1, []
        if probabilities is not None:
            p = probabilities[offset]
            order = np.argsort(-p)
            predicted = int(classes[order[0]])
            confidence, margin = float(p[order[0]]), float(p[order[0]] - p[order[1]])
            if supported and predicted == neighbour and count >= 3 and confidence >= .6 and margin >= .18:
                person = predicted
                evidence = [f"appearance classifier and {count}/{len(nearest)} nearest face-confirmed views agree"]
            elif supported and hints[row] == predicted == neighbour and count >= 2 and confidence >= .4:
                person = predicted
                evidence = ["appearance classifier and nearby face-confirmed frames agree"]
        elif len(classes) == 1 and best_sim >= .65 and float(raw[offset, nearest[0]]) >= .8:
            person = int(classes[0])
            evidence = ["strong appearance match to the known person's reference views"]
        if person >= 0:
            evidence.append(f"nearest appearance similarity {best_sim:.3f}; not a face identity measurement")
        results.append(AppearanceMatch(person, best_sim, tuple(evidence)))
    return results
