"""Exact and near-duplicate detection with keeper selection (spec: duplicate-detection)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DupItem:
    id: str
    kind: str
    sha256: str
    phash: str | None
    pixels: int
    size: int
    captured_at: float
    rel_path: str
    duration: float | None = None
    embedding: np.ndarray | None = None


class _UF:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, a: int) -> int:
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def _keeper_key(it: DupItem):
    return (-it.pixels, -it.size, it.captured_at, len(it.rel_path), it.rel_path)


def _popcount64(x: np.ndarray) -> np.ndarray:
    if hasattr(np, "bitwise_count"):
        return np.bitwise_count(x)
    return np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)  # pragma: no cover


def find_duplicates(
    items: list[DupItem],
    near: bool = True,
    max_distance: int = 4,
    min_cosine: float = 0.90,
    keep: str = "best",
) -> dict[str, str]:
    """Return {duplicate_id: keeper_id}. Keepers are not in the mapping.
    keep: "best" (most pixels, then size, then oldest), "oldest" or "newest" capture time."""
    rank = {
        "oldest": lambda it: (it.captured_at, -it.pixels, it.rel_path),
        "newest": lambda it: (-it.captured_at, -it.pixels, it.rel_path),
    }.get(keep, _keeper_key)
    n = len(items)
    uf = _UF(n)
    by_sha: dict[str, int] = {}
    for i, it in enumerate(items):
        if it.sha256 in by_sha:
            uf.union(by_sha[it.sha256], i)
        else:
            by_sha[it.sha256] = i

    if near:
        for kind in ("image", "video"):
            idx = [i for i, it in enumerate(items) if it.kind == kind and it.phash]
            if len(idx) < 2:
                continue
            hashes = np.array([int(items[i].phash, 16) for i in idx], dtype=np.uint64)
            for a in range(len(idx) - 1):
                d = _popcount64(np.bitwise_xor(hashes[a + 1 :], hashes[a]))
                for off in np.nonzero(d <= max_distance)[0]:
                    i, j = idx[a], idx[a + 1 + int(off)]
                    ii, jj = items[i], items[j]
                    if kind == "video" and abs((ii.duration or 0) - (jj.duration or 0)) > 0.5:
                        continue
                    if ii.embedding is not None and jj.embedding is not None:
                        if float(np.dot(ii.embedding, jj.embedding)) < min_cosine:
                            continue
                    uf.union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(i)
    result: dict[str, str] = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        keeper = min((items[m] for m in members), key=rank)
        for m in members:
            if items[m].id != keeper.id:
                result[items[m].id] = keeper.id
    return result
