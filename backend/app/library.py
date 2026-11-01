"""Library-wide features on top of the analysis cache: natural-language search, find similar, places & trips.

Search and similar use the embeddings every sort already computed (per model cache), so they are instant and need
no extra indexing pass; photos never sorted yet are indexed by running a sort on their folder (no apply needed).
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from .geo import Item, detect_trips, places_for, read_geo
from .scanner import MediaFile

WORKERS = min(8, os.cpu_count() or 2)


def locate_files(cache, files: list[MediaFile]) -> dict[str, dict]:
    """id → {lat, lon, ts} from EXIF, cached per file (size + mtime) in the `geo` table."""
    out: dict[str, dict] = {}
    todo: list[MediaFile] = []
    for f in files:
        hit = cache.get_json("geo", str(f.path), f.size, f.mtime) if f.kind == "image" else {"lat": None, "lon": None, "ts": None}
        if hit is None:
            todo.append(f)
        else:
            out[f.id] = hit
    if todo:
        with ThreadPoolExecutor(WORKERS) as ex:
            for f, g in zip(todo, ex.map(lambda x: read_geo(x.path), todo)):
                cache.put_json("geo", str(f.path), f.size, f.mtime, g)
                out[f.id] = g
    return out


def add_places(geo: dict[str, dict]) -> None:
    """Adds `place` ({city, region, cc, country}) to every located entry (one batched offline lookup)."""
    ids = [i for i, g in geo.items() if g.get("lat") is not None]
    for i, p in zip(ids, places_for([(geo[i]["lat"], geo[i]["lon"]) for i in ids])):
        geo[i]["place"] = p


def trips_for(files: list[MediaFile], geo: dict[str, dict], captured: dict[str, float] | None = None, **kw):
    items = []
    for f in files:
        g = geo.get(f.id) or {}
        ts = g.get("ts") or (captured or {}).get(f.id) or f.mtime
        items.append(Item(f.id, ts, g.get("lat"), g.get("lon"), g.get("place")))
    return detect_trips(items, **kw)


class Library:
    def __init__(self, manager, root: Path):
        self.m = manager
        self.root = root.resolve()
        self._idx: dict[str, tuple] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ embeddings index
    def _index(self, model: str):
        cache = self.m.cache_for(model)
        with cache._lock:
            sig = cache._db.execute("SELECT COUNT(*), COALESCE(MAX(rowid), 0) FROM files WHERE emb IS NOT NULL").fetchone()
        with self._lock:
            cur = self._idx.get(model)
            if cur and cur[0] == sig:
                return cur[1]
        with cache._lock:
            rows = cache._db.execute("SELECT path, meta, emb FROM files WHERE emb IS NOT NULL").fetchall()
        paths, shas, ts, embs = [], [], [], []
        for path, meta, emb in rows:
            v = np.frombuffer(emb, dtype=np.float32)
            if embs and v.shape != embs[0].shape:
                continue
            m = json.loads(meta)
            paths.append(path)
            shas.append(m.get("sha256"))
            ts.append(m.get("captured_at") or 0.0)
            embs.append(v)
        mat = np.vstack(embs).astype(np.float32) if embs else np.zeros((0, 1), np.float32)
        if len(mat):
            mat /= np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
        idx = {"paths": paths, "shas": shas, "ts": ts, "mat": mat}
        with self._lock:
            self._idx[model] = (sig, idx)
        return idx

    def _scope(self, idx, folder: str) -> np.ndarray:
        base = str((self.root / folder).resolve()) if folder else str(self.root)
        prefix = base.rstrip("/") + "/"
        return np.array([p.startswith(prefix) for p in idx["paths"]], dtype=bool) if idx["paths"] else np.zeros(0, bool)

    def _rel(self, abs_path: str) -> str:
        return Path(abs_path).relative_to(self.root).as_posix()

    def _results(self, idx, order, scores, limit: int, skip: set[str] = frozenset()) -> list[dict]:
        out = []
        for i in order:
            p = idx["paths"][i]
            if p in skip or not os.path.exists(p):
                continue
            out.append({"path": self._rel(p), "score": round(float(scores[i]), 4), "thumb": f"/api/thumbs/{idx['shas'][i]}",
                        "captured_at": idx["ts"][i]})
            if len(out) >= limit:
                break
        return out

    def status(self, folder: str, model: str) -> dict:
        idx = self._index(model)
        return {"indexed": int(self._scope(idx, folder).sum()), "model": model}

    def search(self, query: str, folder: str, model: str, limit: int = 60) -> dict:
        t0 = time.time()
        idx = self._index(model)
        mask = self._scope(idx, folder)
        if not mask.any():
            return {"results": [], "indexed": 0, "took_ms": 0}
        emb = self.m.embedder_for(model).embed_texts([f"a photo of {query.strip()}"])[0].astype(np.float32)
        emb /= np.linalg.norm(emb) + 1e-9
        scores = idx["mat"] @ emb
        # OCR: photos whose text contains the query words get a boost (search inside screenshots, signs, documents)
        words = [w for w in re.findall(r"\w{3,}", query.lower())]
        if words:
            cache = self.m.cache
            with cache._lock:
                try:
                    rows = cache._db.execute("SELECT path, data FROM ocr").fetchall()
                except Exception:  # noqa: BLE001 - table appears with the first OCR run
                    rows = []
            pos = {p: i for i, p in enumerate(idx["paths"])}
            for path, data in rows:
                i = pos.get(path)
                if i is None:
                    continue
                text = (json.loads(data) or {}).get("text", "").lower()
                hit = sum(w in text for w in words)
                if hit:
                    scores[i] += 0.12 * hit / len(words) + 0.05
        scores = np.where(mask, scores, -np.inf)
        valid = scores[mask]
        # model-agnostic relevance cut: clearly above the folder's average, at least a dozen results
        cut = float(valid.mean() + 1.2 * valid.std()) if len(valid) > 12 else -np.inf
        order = [i for i in np.argsort(-scores) if np.isfinite(scores[i])]
        keep = [i for n, i in enumerate(order) if n < 12 or scores[i] >= cut]
        return {"results": self._results(idx, keep, scores, limit), "indexed": int(mask.sum()),
                "took_ms": round((time.time() - t0) * 1000)}

    def similar(self, rel_path: str, folder: str, model: str, limit: int = 60, min_sim: float = 0.8) -> dict:
        idx = self._index(model)
        target = str((self.root / rel_path).resolve())
        try:
            i0 = idx["paths"].index(target)
        except ValueError:
            return {"results": [], "indexed": int(self._scope(idx, folder).sum()), "missing": True}
        mask = self._scope(idx, folder)
        scores = np.where(mask, idx["mat"] @ idx["mat"][i0], -np.inf)
        order = [i for i in np.argsort(-scores) if scores[i] >= min_sim and i != i0]
        return {"results": self._results(idx, order, scores, limit, skip={target}), "indexed": int(mask.sum())}

    # ------------------------------------------------------------------ places & trips
    def _files(self, folder: str) -> list[MediaFile]:
        from .scanner import resolve_in_library, scan

        src = resolve_in_library(self.root, folder)
        return scan(self.root, src, self.m.s.output_dir_name, recursive=True, pair_sidecars=False)

    def places(self, folder: str, limit: int = 4000) -> dict:
        files = [f for f in self._files(folder) if f.kind == "image"][:50000]
        geo = locate_files(self.m.cache, files)
        add_places(geo)
        cells: dict[tuple, dict] = {}
        for f in files:
            g = geo.get(f.id) or {}
            if g.get("lat") is None:
                continue
            key = (round(g["lat"], 2), round(g["lon"], 2))
            c = cells.get(key)
            if c is None:
                pl = g.get("place") or {}
                c = cells[key] = {"lat": 0.0, "lon": 0.0, "count": 0, "city": pl.get("city"), "country": pl.get("country"),
                                  "cc": pl.get("cc"), "paths": []}
            c["lat"] += g["lat"]
            c["lon"] += g["lon"]
            c["count"] += 1
            if len(c["paths"]) < 60:
                c["paths"].append(f.rel_path)
        points = []
        for c in sorted(cells.values(), key=lambda c: -c["count"])[:limit]:
            c["lat"], c["lon"] = round(c["lat"] / c["count"], 5), round(c["lon"] / c["count"], 5)
            points.append(c)
        located = sum(c["count"] for c in points)
        countries: dict[str, int] = {}
        for c in points:
            if c["country"]:
                countries[c["country"]] = countries.get(c["country"], 0) + c["count"]
        return {"points": points, "photos": len(files), "located": located,
                "countries": sorted(({"name": k, "count": v} for k, v in countries.items()), key=lambda x: -x["count"])}

    def trips(self, folder: str, away_km: float = 80.0, gap_hours: float = 36.0, min_photos: int = 5) -> dict:
        files = self._files(folder)
        geo = locate_files(self.m.cache, files)
        add_places(geo)
        trips, home = trips_for(files, geo, away_km=away_km, gap_hours=gap_hours, min_photos=min_photos)
        by_id = {f.id: f for f in files}
        out = []
        for t in sorted(trips, key=lambda t: -t.start):
            imgs = [by_id[i].rel_path for i in t.ids if by_id[i].kind == "image"]
            out.append({"name": t.name(), "start": t.start, "end": t.end, "count": len(t.ids), "center": t.center,
                        "countries": list(t.countries), "samples": imgs[:8], "paths": [by_id[i].rel_path for i in t.ids][:500]})
        located = sum(1 for g in geo.values() if g.get("lat") is not None)
        home_place = places_for([home])[0] if home else None
        return {"trips": out, "home": {"lat": home[0], "lon": home[1], **(home_place or {})} if home else None,
                "photos": len(files), "located": located}
