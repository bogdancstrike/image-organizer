"""FastAPI application: REST + SSE + static UI."""
from __future__ import annotations

import json
import logging
import re
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .categories import CategorySetIn, CategoryStore, all_presets
from .config import Settings, load_settings
from .embedder import get_clip_embedder
from .jobs import BusyError, JobManager
from .llm import LLMClient
from .organizer import list_runs, undo_run
from .scanner import PathError, list_folders

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class JobOptions(BaseModel):
    min_confidence: float = Field(0.30, ge=0.0, le=1.0)
    near_duplicates: bool = True
    near_dup_distance: int = Field(4, ge=0, le=16)
    split_media: bool = True
    ai_assist: bool = False
    ai_max_files: int = Field(200, ge=1, le=2000)
    date_granularity: Literal["year", "month", "day"] = "month"
    max_clusters: int = Field(12, ge=2, le=30)


class JobRequest(BaseModel):
    source: str = ""
    strategy: Literal["preset", "custom", "auto", "date"] = "preset"
    set_id: str | None = "lifestyle"
    options: JobOptions = Field(default_factory=JobOptions)


class ApplyRequest(BaseModel):
    mode: Literal["move", "copy"] = "move"


def create_app(settings: Settings | None = None, embedder_factory=None, llm_factory=None) -> FastAPI:
    s = settings or load_settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    store = CategoryStore(s.data_dir / "category_sets.json")

    if embedder_factory is None:
        def embedder_factory():
            return get_clip_embedder(str(s.model_dir) if s.model_dir else None)

    if llm_factory is None:
        def llm_factory():
            if not s.ai_available:
                return None
            return LLMClient(s.openai_api_key, s.openai_model, s.reasoning_effort)

    manager = JobManager(s, embedder_factory, store, llm_factory)
    app = FastAPI(title="Auto Image Organizer", version=__version__)
    app.state.manager = manager
    app.state.settings = s

    # ---------------------------------------------------------------- meta
    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "version": __version__,
            "ai_available": s.ai_available,
            "model": s.openai_model if s.ai_available else None,
            "library_ok": s.library_root.is_dir(),
            "library_name": s.library_name,
            "output_dir": s.output_dir_name,
        }

    @app.get("/api/folders")
    def folders(path: str = Query("")):
        try:
            return list_folders(s.library_root, path, s.output_dir_name)
        except PathError as exc:
            raise HTTPException(400, str(exc)) from exc

    # ---------------------------------------------------------- categories
    @app.get("/api/presets")
    def presets():
        return all_presets()

    @app.get("/api/category-sets")
    def list_sets():
        return store.list()

    @app.post("/api/category-sets", status_code=201)
    def create_set(body: CategorySetIn):
        return store.upsert(None, body)

    @app.put("/api/category-sets/{set_id}")
    def update_set(set_id: str, body: CategorySetIn):
        try:
            return store.upsert(set_id, body)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.delete("/api/category-sets/{set_id}", status_code=204)
    def delete_set(set_id: str):
        if not store.delete(set_id):
            raise HTTPException(404, "not found")

    # ---------------------------------------------------------------- jobs
    @app.post("/api/jobs", status_code=201)
    def start_job(body: JobRequest):
        try:
            job = manager.start(body.model_dump())
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from exc
        except PathError as exc:
            raise HTTPException(400, str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        return {"id": job.id}

    def _job(job_id: str):
        job = manager.get(job_id)
        if not job:
            raise HTTPException(404, "job not found")
        return job

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str, plan: bool = True):
        return _job(job_id).snapshot(include_plan=plan)

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        _job(job_id)
        return {"cancelled": manager.cancel(job_id)}

    @app.get("/api/jobs/{job_id}/events")
    async def job_events(job_id: str, request: Request):
        job = _job(job_id)

        async def gen():
            seq = 0
            yield "retry: 2000\n\n"
            while True:
                if await request.is_disconnected():
                    break
                evs = await run_in_threadpool(job.events_since, seq, 10.0)
                if evs:
                    seq = evs[-1]["seq"] + 1
                    yield f"data: {json.dumps(evs, ensure_ascii=False)}\n\n"
                    if job.finished and seq >= len(job.events):
                        yield "event: end\ndata: {}\n\n"
                        break
                elif job.finished:
                    yield "event: end\ndata: {}\n\n"
                    break
                else:
                    yield ": ping\n\n"

        return StreamingResponse(
            gen(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/jobs/{job_id}/apply")
    async def apply_job(job_id: str, body: ApplyRequest):
        _job(job_id)
        try:
            journal = await run_in_threadpool(manager.apply, job_id, body.mode)
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {k: journal[k] for k in ("run_id", "mode", "status", "created_at")} | {
            "moved": len(journal["ops"]), "failed": journal["failed"], "skipped": journal["skipped"],
        }

    # --------------------------------------------------------------- runs
    @app.get("/api/runs")
    def runs():
        return list_runs(s.journals_dir)

    @app.post("/api/runs/{run_id}/undo")
    async def undo(run_id: str):
        if not re.fullmatch(r"[0-9A-Za-z-]+", run_id):
            raise HTTPException(400, "bad run id")
        try:
            j = await run_in_threadpool(undo_run, s.library_root, s.journals_dir, run_id)
        except FileNotFoundError as exc:
            raise HTTPException(404, "run not found") from exc
        return {"run_id": run_id, "status": j["status"], "undo": j.get("undo")}

    # ------------------------------------------------------------- thumbs
    @app.get("/api/thumbs/{sha}")
    def thumb(sha: str):
        if not SHA_RE.match(sha):
            raise HTTPException(400, "bad id")
        p = manager.thumb_path(sha)
        if not p.exists():
            raise HTTPException(404, "no thumbnail")
        return FileResponse(p, media_type="image/webp", headers={"Cache-Control": "public, max-age=31536000, immutable"})

    if s.static_dir and s.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(s.static_dir), html=True), name="ui")

    return app
# Run with: uvicorn --factory app.main:create_app
