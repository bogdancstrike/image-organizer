"""History HTTP routes."""
from __future__ import annotations

import re
from fastapi import HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from app.infrastructure.database import OUTCOMES, history, summarize
from app.organization.operations import empty_trash, undo_run
from fastapi import APIRouter
from app.api.context import Runtime


def create_router(ctx: Runtime) -> APIRouter:
    router = APIRouter(tags=["history"])
    s = ctx.settings
    manager = ctx.manager
    db = ctx.db

    @router.get("/api/runs")
    def runs():
        return db.runs()


    @router.get("/api/history")
    def get_history(outcome: str = Query("all"), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
        if outcome != "all" and outcome not in OUTCOMES:
            raise HTTPException(400, "unknown outcome")
        return history(db, outcome, limit, offset)


    @router.get("/api/stats")
    def stats():
        return summarize(db.job_stats(), db.runs())


    @router.post("/api/runs/{run_id}/undo")
    async def undo(run_id: str):
        if not re.fullmatch(r"[0-9A-Za-z-]+", run_id):
            raise HTTPException(400, "bad run id")
        try:
            j = await run_in_threadpool(undo_run, s.library_root, s.journals_dir, run_id)
            ctx.sync_run(run_id)
            manager.mark_undone(run_id)
        except FileNotFoundError as exc:
            raise HTTPException(404, "run not found") from exc
        return {"run_id": run_id, "status": j["status"], "undo": j.get("undo")}


    @router.post("/api/runs/{run_id}/empty-trash")
    async def run_empty_trash(run_id: str):
        """Permanently delete the duplicates this run sent to the trash (irreversible)."""
        if not re.fullmatch(r"[0-9A-Za-z-]+", run_id):
            raise HTTPException(400, "bad run id")
        try:
            res = await run_in_threadpool(empty_trash, s.library_root, s.journals_dir, run_id)
            ctx.sync_run(run_id)
            return res
        except FileNotFoundError as exc:
            raise HTTPException(404, "run not found") from exc


    return router
