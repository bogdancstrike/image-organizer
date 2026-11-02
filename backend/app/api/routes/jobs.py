"""Jobs HTTP routes."""
from __future__ import annotations

import json
from fastapi import HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from app.organization.jobs import BusyError
from app.media.scanning import PathError
from app.api.schemas import ApplyRequest, JobRequest, ReassignRequest, RenameRequest
from fastapi import APIRouter
from app.api.context import Runtime


def create_router(ctx: Runtime) -> APIRouter:
    router = APIRouter(tags=["jobs"])
    manager = ctx.manager
    db = ctx.db

    @router.post("/api/jobs", status_code=201)
    def start_job(body: JobRequest):
        try:
            req = body.model_dump()
            if body.strategy == "rules" and manager.llm_factory() is None:
                raise HTTPException(400, "Prompt rules require AI; configure OPENAI_API_KEY in .env")
            ref_id = req["options"].get("people_reference")
            if ref_id and req["strategy"] == "people":
                ref = db.get_face_ref(ref_id)
                if not ref:
                    raise HTTPException(404, "reference face not found; upload it again")
                req["options"]["_people_ref"] = ref
            job = manager.start(req)
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


    @router.get("/api/jobs/{job_id}")
    def get_job(job_id: str, plan: bool = True):
        return _job(job_id).snapshot(include_plan=plan)


    @router.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        _job(job_id)
        return {"cancelled": manager.cancel(job_id)}


    @router.get("/api/jobs/{job_id}/events")
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


    @router.patch("/api/jobs/{job_id}/categories/{category_id}")
    def rename_category(job_id: str, category_id: str, body: RenameRequest):
        _job(job_id)
        try:
            return manager.rename_category(job_id, category_id, body.name)
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc


    @router.patch("/api/jobs/{job_id}/plan")
    def reassign(job_id: str, body: ReassignRequest):
        _job(job_id)
        try:
            return manager.reassign(job_id, body.file_ids, body.category_id)
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc


    @router.post("/api/jobs/{job_id}/apply")
    async def apply_job(job_id: str, body: ApplyRequest):
        _job(job_id)
        try:
            journal = await run_in_threadpool(manager.apply, job_id, body.mode)
            ctx.sync_run(journal["run_id"])
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {k: journal[k] for k in ("run_id", "mode", "status", "created_at")} | {
            "moved": len([o for o in journal["ops"] if "src" in o]), "failed": journal["failed"], "skipped": journal["skipped"],
        }


    return router
