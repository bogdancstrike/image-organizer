"""Application composition root: wire services, HTTP adapters and static delivery."""
from __future__ import annotations

import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.context import Runtime
from app.api.routes import system, catalog, jobs, faces, library, media, history, suggestions
from app.infrastructure.config import Settings, load_settings
from app.infrastructure.category_store import CategoryStore
from app.infrastructure.database import AppDB
from app.infrastructure.embeddings import get_clip_embedder
from app.infrastructure.llm import LLMClient
from app.organization.jobs import JobManager
from app.organization.operations import list_runs
from app.library.service import Library

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
UI_ROUTES = {"sort", "review", "library", "categories", "history", "statistics", "settings"}


def create_app(settings: Settings | None = None, embedder_factory=None, llm_factory=None) -> FastAPI:
    s = settings or load_settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    store = CategoryStore(s.data_dir / "category_sets.json")
    if embedder_factory is None:
        def embedder_factory(model: str = "clip"):
            return get_clip_embedder(str(s.model_dir) if s.model_dir else None, model, s.device)
    if llm_factory is None:
        def llm_factory():
            return LLMClient(s.openai_api_key, s.openai_model, s.reasoning_effort) if s.ai_available else None
    manager = JobManager(s, embedder_factory, store, llm_factory)
    db = AppDB(s.data_dir / "app.db")
    manager.db = db
    if not db.has_runs():
        for run in list_runs(s.journals_dir):
            db.upsert_run(run)
    app = FastAPI(title="Auto Image Organizer", version=__version__)
    runtime = Runtime(s, manager, store, db, Library(manager, s.library_root))
    app.state.runtime = runtime
    app.state.manager = manager
    app.state.settings = s
    for module in (system, catalog, jobs, faces, library, media, history, suggestions):
        app.include_router(module.create_router(runtime))

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
