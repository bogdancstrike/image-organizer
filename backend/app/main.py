"""FastAPI application: REST + SSE + static UI."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps
from pydantic import BaseModel, Field, field_validator

from . import __version__
from .categories import CategorySetIn, CategoryStore, all_presets
from .config import Settings, load_settings
from .embedder import get_clip_embedder
from .jobs import BusyError, JobManager
from .llm import LLMClient
from .organizer import empty_trash, list_runs, undo_run
from .media import open_any
from .scanner import PathError, list_folders, media_kind

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
UI_ROUTES = {"sort", "review", "categories", "history", "settings"}


class QualityOptions(BaseModel):
    enabled: bool = False  # run checks with any strategy (always on for "cull")
    blur: bool = True
    eyes_closed: bool = True
    exposure: bool = True
    smiles: bool = True
    blur_threshold: float = Field(0.5, ge=0.0, le=1.0)
    blink_threshold: float = Field(0.5, ge=0.05, le=1.0)
    smile_threshold: float = Field(0.5, ge=0.05, le=1.0)
    action: Literal["reject", "tag"] = "reject"  # reject = move to _Rejects/<reason>
    faces_rule: Literal["any", "main"] = "any"  # whose eyes/smile count: any face, or the main (largest) face
    dark_threshold: float = Field(0.18, ge=0.0, le=0.5)
    bright_threshold: float = Field(0.85, ge=0.5, le=1.0)
    bursts: bool = True  # best-of-burst: keep the best of near-identical shots seconds apart
    burst_seconds: float = Field(2.0, ge=0.2, le=30.0)
    burst_similarity: float = Field(0.9, ge=0.75, le=0.99)
    keeper_min_stars: int = Field(0, ge=0, le=5)  # cull: keepers below this go to "Maybe" (0 = off)
    noise_check: bool = False
    noise_threshold: float = Field(0.045, ge=0.005, le=0.2)
    tilt_check: bool = False  # experimental: consistent horizon lines leaning 1.5–8°
    tilt_tolerance: float = Field(1.5, ge=0.5, le=8.0)
    face_crop: bool = False
    picks_percent: float = Field(0, ge=0, le=50)  # cull: top X% of keepers go to "Picks ★"
    similar_any_time: bool = False  # best-of-similar regardless of time, not just bursts
    write_xmp: bool = False  # on apply, write .xmp sidecars with star rating and color label


class AIOptions(BaseModel):
    model: str | None = Field(None, pattern=r"^[A-Za-z0-9._:-]{1,64}$")  # None = server default
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None
    naming_prompt: str = Field("", max_length=4000)  # full template; "" = default (GET /api/ai/defaults)
    assist_prompt: str = Field("", max_length=4000)
    assist_scope: Literal["unsure", "all"] = "unsure"  # AI assist on uncertain files only, or on every file
    naming_instructions: str = Field("", max_length=1500)  # extra guidance for naming auto groups
    assist_instructions: str = Field("", max_length=1500)  # extra guidance for AI assist
    assist_batch: int = Field(12, ge=1, le=24)  # thumbnails per assist request


class JobOptions(BaseModel):
    min_confidence: float = Field(0.30, ge=0.0, le=1.0)
    near_duplicates: bool = True
    near_dup_distance: int = Field(4, ge=0, le=16)
    split_media: bool = True
    duplicates_action: Literal["folder", "with_original", "keep", "delete"] = "folder"
    duplicate_keep: Literal["best", "oldest", "newest"] = "best"
    ai_assist: bool = False
    ai_max_files: int = Field(200, ge=1, le=5000)
    date_granularity: Literal["year", "month", "day"] = "month"
    max_clusters: int = Field(12, ge=2, le=30)
    focus: Literal["auto", "scene", "framing", "outfit", "lighting", "subject"] = "auto"  # what auto groups by
    granularity: Literal["coarse", "normal", "fine"] = "normal"
    ai: AIOptions = Field(default_factory=AIOptions)
    # where the category folders go: None = server default (OUTPUT_DIR_NAME), "" = directly in the chosen folder
    output_dir: str | None = Field(None, max_length=60, pattern=r'^[^/\\:*?"<>|]*$')
    recursive: bool = True
    pair_sidecars: bool = True  # keep RAW+JPEG pairs and .xmp sidecars together
    quality: QualityOptions = Field(default_factory=QualityOptions)

    @field_validator("output_dir")
    @classmethod
    def _no_dots(cls, v: str | None) -> str | None:
        if v is not None and v.strip() in (".", ".."):
            raise ValueError("invalid folder name")
        return v


class JobRequest(BaseModel):
    source: str = ""
    strategy: Literal["preset", "custom", "auto", "date", "cull"] = "preset"
    set_id: str | None = "lifestyle"
    options: JobOptions = Field(default_factory=JobOptions)


class ReassignRequest(BaseModel):
    file_ids: list[str] = Field(min_length=1, max_length=20000)
    category_id: str


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
            "library_host_path": s.library_host_path,
            "faces_available": Path(os.environ.get("FACE_MODEL", "/models/face_landmarker.task")).exists(),
            "output_dir": s.output_dir_name,
        }

    _models_cache: dict = {}

    @app.get("/api/ai/defaults")
    def ai_defaults():
        """Default prompt templates, so the UI can show them pre-filled and editable."""
        from .llm import ASSIST_FORMAT, DEFAULT_ASSIST_PROMPT, DEFAULT_NAMING_PROMPT, NAMING_FORMAT

        return {
            "naming_prompt": DEFAULT_NAMING_PROMPT,
            "assist_prompt": DEFAULT_ASSIST_PROMPT,
            "naming_placeholders": ["{theme}", "{groups}", "{focus}"],
            "assist_placeholders": ["{count}", "{folders}"],
            "naming_format": NAMING_FORMAT.strip(),
            "assist_format": ASSIST_FORMAT.strip(),
        }

    @app.get("/api/ai/models")
    def ai_models():
        """Vision-capable chat models the configured key can use (cached), for the Settings → AI picker."""
        if not s.ai_available:
            return {"default": None, "models": []}
        if "models" not in _models_cache:
            try:
                from openai import OpenAI

                ids = [m.id for m in OpenAI(api_key=s.openai_api_key, timeout=15).models.list().data]
                keep = [i for i in ids if i.startswith(("gpt-5", "gpt-6", "gpt-4o", "gpt-4.1", "o4"))
                        and not any(x in i for x in ("audio", "realtime", "tts", "search", "transcribe", "image"))]
                _models_cache["models"] = sorted(set(keep), reverse=True)
            except Exception as exc:  # noqa: BLE001
                return {"default": s.openai_model, "models": [s.openai_model], "error": str(exc)}
        return {"default": s.openai_model, "models": _models_cache["models"]}

    @app.get("/api/folders")
    def folders(path: str = Query("")):
        try:
            return list_folders(s.library_root, path, s.output_dir_name)
        except PathError as exc:
            raise HTTPException(400, str(exc)) from exc

    # ---------------------------------------------------------- categories
    @app.get("/api/presets")
    def presets():
        return store.presets()

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
        """Deletes a custom set, or resets an edited preset to its default."""
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

    @app.patch("/api/jobs/{job_id}/plan")
    def reassign(job_id: str, body: ReassignRequest):
        _job(job_id)
        try:
            return manager.reassign(job_id, body.file_ids, body.category_id)
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/jobs/{job_id}/apply")
    async def apply_job(job_id: str, body: ApplyRequest):
        _job(job_id)
        try:
            journal = await run_in_threadpool(manager.apply, job_id, body.mode)
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {k: journal[k] for k in ("run_id", "mode", "status", "created_at")} | {
            "moved": len([o for o in journal["ops"] if "src" in o]), "failed": journal["failed"], "skipped": journal["skipped"],
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

    @app.post("/api/runs/{run_id}/empty-trash")
    async def run_empty_trash(run_id: str):
        """Permanently delete the duplicates this run sent to the trash (irreversible)."""
        if not re.fullmatch(r"[0-9A-Za-z-]+", run_id):
            raise HTTPException(400, "bad run id")
        try:
            return await run_in_threadpool(empty_trash, s.library_root, s.journals_dir, run_id)
        except FileNotFoundError as exc:
            raise HTTPException(404, "run not found") from exc

    # ------------------------------------------------------------- thumbs
    @app.get("/api/thumbs/{sha}")
    def thumb(sha: str):
        if not SHA_RE.match(sha):
            raise HTTPException(400, "bad id")
        p = manager.thumb_path(sha)
        if not p.exists():
            raise HTTPException(404, "no thumbnail")
        return FileResponse(p, media_type="image/webp", headers={"Cache-Control": "public, max-age=31536000, immutable"})

    @app.get("/api/preview")
    def preview(path: str = Query(..., min_length=1)):
        """Large view for the lightbox: photos as a cached 1600 px JPEG, videos streamed (range requests)."""
        root = s.library_root
        p = (root / path.lstrip("/")).resolve()
        if not (root in p.parents) or not p.is_file():
            raise HTTPException(404, "file not found (it may have been moved)")
        kind = media_kind(p.name)
        if kind == "video":
            return FileResponse(p)
        if kind != "image":
            raise HTTPException(400, "not a media file")
        st = p.stat()
        key = hashlib.sha1(f"{p}|{st.st_size}|{st.st_mtime}".encode()).hexdigest()
        out = s.data_dir / "previews" / key[:2] / f"{key}.jpg"
        if not out.exists():
            try:
                with open_any(p) as im:
                    if im.format == "JPEG":
                        im.draft("RGB", (2000, 2000))
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    im.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    im.save(out, "JPEG", quality=85)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(422, f"cannot render preview: {exc}") from exc
        return FileResponse(out, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})

    if s.static_dir and s.static_dir.is_dir():
        index = s.static_dir / "index.html"

        # client-side routes (/sort, /review, …) all load the single-page app
        @app.get("/{tab}", include_in_schema=False)
        def spa_route(tab: str):
            if tab in UI_ROUTES:
                return FileResponse(index, headers={"Cache-Control": "no-cache"})
            f = (s.static_dir / tab).resolve()
            if s.static_dir.resolve() in f.parents and f.is_file():
                return FileResponse(f)
            raise HTTPException(404, "not found")

        app.mount("/", StaticFiles(directory=str(s.static_dir), html=True), name="ui")

    return app
# Run with: uvicorn --factory app.main:create_app
