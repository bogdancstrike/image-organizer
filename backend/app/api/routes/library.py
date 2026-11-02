"""Library HTTP routes."""
from __future__ import annotations

from fastapi import HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter
from app.api.context import Runtime


def create_router(ctx: Runtime) -> APIRouter:
    router = APIRouter(tags=["library"])
    lib = ctx.library
    _folder = ctx.folder
    _model = ctx.model

    @router.get("/api/library/status")
    def library_status(folder: str = "", model: str = "clip"):
        return lib.status(_folder(folder), _model(model))


    @router.get("/api/library/tags")
    def library_tags(folder: str = "", model: str = "clip"):
        return lib.tag_facets(_folder(folder), _model(model))


    @router.get("/api/library/search")
    async def library_search(q: str = Query(..., min_length=1, max_length=200), folder: str = "", model: str = "clip",
                             limit: int = Query(60, ge=1, le=300), tag: list[str] = Query(default=[], max_length=12)):
        try:
            return await run_in_threadpool(lib.search, q, _folder(folder), _model(model), limit, tag)
        except RuntimeError as exc:  # model not available
            raise HTTPException(503, str(exc)) from exc


    @router.get("/api/library/similar")
    async def library_similar(path: str = Query(..., min_length=1), folder: str = "", model: str = "clip",
                              limit: int = Query(60, ge=1, le=300), min_sim: float = Query(0.8, ge=0.5, le=0.99)):
        return await run_in_threadpool(lib.similar, path, _folder(folder), _model(model), limit, min_sim)


    @router.get("/api/library/places")
    async def library_places(folder: str = ""):
        return await run_in_threadpool(lib.places, _folder(folder))


    @router.get("/api/library/trips")
    async def library_trips(folder: str = "", away_km: float = Query(80, ge=10, le=2000), gap_hours: float = Query(36, ge=6, le=240),
                            min_photos: int = Query(5, ge=1, le=200)):
        return await run_in_threadpool(lib.trips, _folder(folder), away_km, gap_hours, min_photos)


    return router
