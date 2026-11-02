"""Optional, complete aesthetic evaluation using the bundled CLIP tower and local caches."""
from __future__ import annotations

import numpy as np

from app.culling.quality import score
from app.infrastructure.aesthetics import SPACE, VERSION, get_predictor
from app.media.decoding import load_for_quality

def analyze(manager, job, ordered, quality, rules, current_embedder) -> None:
    candidates = sorted((row for row in ordered if row[0].kind == "image" and row[0].id in quality),
                        key=lambda row: (-score(quality[row[0].id], rules), row[0].rel_path))
    if not candidates:
        return
    # Every nonduplicate photo is evaluated; alternate encoders obtain their own cached CLIP vectors.
    reuse = getattr(current_embedder, "embedding_space", None) == SPACE
    selected = candidates
    embedder = current_embedder if reuse else manager.embedder_for("clip")
    if getattr(embedder, "embedding_space", None) != SPACE:
        raise ValueError("CLIP embedding-space compatibility could not be verified")
    predictor = get_predictor()
    cache = manager.cache_for("clip")
    manager._phase(job, "aesthetics")
    done = 0
    for start in range(0, len(selected), 16):
        if job.cancel_requested:
            return
        batch = selected[start:start + 16]
        pending, images, vectors = [], [], []
        for f, analysis, embedding in batch:
            saved = cache.get_json("aesthetics", str(f.path), f.size, f.mtime)
            if saved and saved.get("v") == VERSION and np.isfinite(saved.get("raw", np.nan)):
                raw = float(saved["raw"])
                quality[f.id].features.update(aesthetic=float(np.clip(float(raw) / 10, 0, 1)))
                done += 1
                continue
            pending.append((f, analysis))
            cached = cache.get(str(f.path), f.size, f.mtime) if not reuse else None
            vectors.append(embedding if reuse else cached[1] if cached else None)
            if vectors[-1] is None:
                images.append(load_for_quality(f.path, 448))
        if pending:
            inferred = iter(embedder.embed_images(images)) if images else iter(())
            E = np.vstack([vector if vector is not None else next(inferred) for vector in vectors])
            ratings = predictor.predict(E, SPACE)
            for (f, analysis), embedding, raw in zip(pending, E, ratings):
                cache.put_json("aesthetics", str(f.path), f.size, f.mtime, {"v": VERSION, "raw": float(raw)})
                if not reuse:
                    cache.put(str(f.path), f.size, f.mtime, analysis, embedding)
                quality[f.id].features.update(aesthetic=float(np.clip(float(raw) / 10, 0, 1)))
                done += 1
        job.emit("progress", analyzed=done, total=len(selected), stage="aesthetics")
    job.stats["aesthetic_scored"] = done
