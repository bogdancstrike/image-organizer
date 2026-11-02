"""Explicit per-application dependencies and HTTP input validation."""
from __future__ import annotations

from dataclasses import dataclass
from fastapi import HTTPException

from app.infrastructure.config import Settings
from app.infrastructure.category_store import CategoryStore
from app.infrastructure.database import AppDB
from app.organization.jobs import JobManager
from app.organization.operations import list_runs
from app.library.service import Library
from app.media.scanning import PathError, resolve_in_library


@dataclass
class Runtime:
    settings: Settings
    manager: JobManager
    store: CategoryStore
    db: AppDB
    library: Library

    def sync_run(self, run_id: str) -> None:
        for run in list_runs(self.settings.journals_dir):
            if run["run_id"] == run_id:
                self.db.upsert_run(run)

    def folder(self, folder: str) -> str:
        try:
            path = resolve_in_library(self.settings.library_root, folder)
        except PathError as exc:
            raise HTTPException(400, str(exc)) from exc
        return "" if path == self.settings.library_root.resolve() else path.relative_to(self.settings.library_root.resolve()).as_posix()

    @staticmethod
    def model(model: str) -> str:
        if model not in ("clip", "siglip2"):
            raise HTTPException(400, "unknown model")
        return model
