"""Suggestions HTTP routes."""
from __future__ import annotations

from fastapi import HTTPException, Query
from app.catalog.presets import RECIPES_BY_ID, SHOOT_THEMES, THEME_TO_RECIPE
from app.media.scanning import PathError, resolve_in_library, scan
from fastapi import APIRouter
from app.api.context import Runtime


def create_router(ctx: Runtime) -> APIRouter:
    router = APIRouter(tags=["suggestions"])
    s = ctx.settings
    manager = ctx.manager

    @router.get("/api/suggest")
    def suggest(path: str = Query(""), recursive: bool = True, sample: int = Query(40, ge=8, le=120)):
        """Look at a sample of the folder and recommend recipes, so users don't have to know the options."""
        import numpy as np

        from app.recognition import classification as classify
        from app.recognition.ports import normalize

        try:
            src = resolve_in_library(s.library_root, path)
        except PathError as exc:
            raise HTTPException(400, str(exc)) from exc
        files = scan(s.library_root, src, s.output_dir_name, recursive=recursive)
        photos = [f for f in files if f.kind == "image"]
        videos = len(files) - len(photos)
        if not photos:
            return {"total": len(files), "photos": 0, "videos": videos, "suggestions": [
                {"recipe": "by-date" if videos else "camera-roll", "reason": {"key": "no_photos"}}]}
        step = max(1, len(photos) // sample)
        picked = photos[::step][:sample]
        embs, shots = [], 0
        emb = manager.embedder_for("clip")
        for f in picked:
            kind, _, payload, e = manager._analyze_one(f)
            if kind == "error":
                continue
            if kind == "new":
                e = normalize(emb.embed_images(payload.frames).mean(axis=0))
                manager.cache.put(str(f.path), f.size, f.mtime, payload.analysis, e)
                analysis = payload.analysis
            else:
                analysis = payload
            embs.append(e)
            shots += int(analysis.is_screenshot)
        if not embs:
            return {"total": len(files), "photos": len(photos), "videos": videos, "suggestions": []}
        E = np.vstack(embs)
        theme, conf = classify.collection_theme(E, emb)
        probe = emb.embed_texts(["a photo of a person", "a screenshot or a document with text", "a landscape or object with no people"])
        share = (np.argmax(E @ probe.T, axis=1)[:, None] == np.arange(3)).mean(axis=0)
        people_share, text_share = float(share[0]), float(max(share[1], shots / len(embs)))
        out: list[dict] = []
        if text_share >= 0.35:
            out.append({"recipe": "documents", "reason": {"key": "text", "pct": round(text_share * 100)}})
        main = THEME_TO_RECIPE.get(theme, "camera-roll")
        out.append({"recipe": main, "reason": {"key": "theme", "theme": theme, "pct": round(conf * 100)}})
        if theme in SHOOT_THEMES:
            out.append({"recipe": "photoshoot", "reason": {"key": "shoot", "theme": theme}})
        if people_share >= 0.6:
            out.append({"recipe": "people", "reason": {"key": "people", "pct": round(people_share * 100)}})
        out.append({"recipe": "discover", "reason": {"key": "discover"}})
        seen, uniq = set(), []
        for x in out:
            if x["recipe"] not in seen and x["recipe"] in RECIPES_BY_ID:
                seen.add(x["recipe"])
                uniq.append(x)
        from app.library.service import locate_files

        geo = locate_files(manager.cache, picked)
        gps_share = sum(1 for g in geo.values() if g.get("lat") is not None) / max(1, len(picked))
        return {"total": len(files), "photos": len(photos), "videos": videos, "sampled": len(embs), "theme": theme,
                "people_share": round(people_share, 2), "text_share": round(text_share, 2), "gps_share": round(gps_share, 2),
                "suggestions": uniq[:3]}


    return router
