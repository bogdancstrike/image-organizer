"""Faces HTTP routes."""
from __future__ import annotations

import hashlib
from fastapi import HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter
from app.api.context import Runtime


def create_router(ctx: Runtime) -> APIRouter:
    router = APIRouter(tags=["faces"])
    manager = ctx.manager
    db = ctx.db

    @router.get("/api/faces")
    def list_faces():
        return [{k: r[k] for k in ("id", "name", "cover")} for r in db.face_refs()]


    @router.post("/api/faces", status_code=201)
    async def add_face(request: Request, name: str = Query("", max_length=60)):
        """Body: the raw image bytes (any common photo format, ≤ 25 MB)."""
        data = await request.body()
        if not data:
            raise HTTPException(400, "empty upload")
        if len(data) > 25 << 20:
            raise HTTPException(413, "photo too large (max 25 MB)")
        try:
            info = await run_in_threadpool(manager.reference_face, data)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        ref = {"id": hashlib.sha1(data).hexdigest()[:12], "name": name.strip() or "This person", **info}
        db.add_face_ref(ref)
        return {k: ref[k] for k in ("id", "name", "cover", "faces_in_photo")}


    @router.delete("/api/faces/{ref_id}", status_code=204)
    def delete_face(ref_id: str):
        if not db.delete_face_ref(ref_id):
            raise HTTPException(404, "not found")


    return router
