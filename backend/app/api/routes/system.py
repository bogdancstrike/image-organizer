"""System HTTP routes."""
from __future__ import annotations

import json
import os
from pathlib import Path
from fastapi import HTTPException
from app import __version__
from app.organization.jobs import BusyError
from app.infrastructure.ocr import get_text_reader
from app.infrastructure.identity import get_face_identifier
from app.api.schemas import RESET_PHRASE, ResetRequest
from fastapi import APIRouter
from app.api.context import Runtime

import logging
log = logging.getLogger("app.api.system")


def create_router(ctx: Runtime) -> APIRouter:
    router = APIRouter(tags=["system"])
    s = ctx.settings
    manager = ctx.manager
    store = ctx.store
    db = ctx.db
    _models_cache: dict = {}

    @router.get("/api/health")
    def health():
        return {
            "status": "ok",
            "device": s.device,
            "version": __version__,
            "ai_available": s.ai_available,
            "model": s.openai_model if s.ai_available else None,
            "library_ok": s.library_root.is_dir(),
            "library_name": s.library_name,
            "library_host_path": s.library_host_path,
            "faces_available": Path(os.environ.get("FACE_MODEL", "/models/face_landmarker.task")).exists(),
            "people_available": get_face_identifier().available,
            "ocr_available": get_text_reader().available,
            "models": ["clip", "siglip2"],
            "output_dir": s.output_dir_name,
        }


    @router.get("/api/ai/defaults")
    def ai_defaults():
        """Default prompt templates, so the UI can show them pre-filled and editable."""
        from app.infrastructure.llm import ASSIST_FORMAT, DEFAULT_ASSIST_PROMPT, DEFAULT_NAMING_PROMPT, NAMING_FORMAT

        return {
            "naming_prompt": DEFAULT_NAMING_PROMPT,
            "assist_prompt": DEFAULT_ASSIST_PROMPT,
            "naming_placeholders": ["{theme}", "{groups}", "{focus}"],
            "assist_placeholders": ["{count}", "{folders}"],
            "naming_format": NAMING_FORMAT.strip(),
            "assist_format": ASSIST_FORMAT.strip(),
        }


    @router.get("/api/ai/models")
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


    @router.get("/api/settings")
    def get_settings():
        return db.get_setting("ui", {})


    @router.put("/api/settings")
    def put_settings(body: dict):
        if len(json.dumps(body)) > 200_000:
            raise HTTPException(413, "settings too large")
        db.set_setting("ui", body)
        return {"ok": True}


    @router.post("/api/admin/reset")
    def factory_reset(body: ResetRequest):
        """Back to a freshly deployed state. Photos and folders on disk are never touched."""
        if body.confirm.strip().lower() != RESET_PHRASE:
            raise HTTPException(400, f'type "{RESET_PHRASE}" to confirm')
        try:
            manager.factory_reset(body.include_cache)
        except BusyError as exc:
            raise HTTPException(409, str(exc)) from exc
        db.wipe()
        store.wipe()
        for j in s.journals_dir.glob("*.json"):
            j.unlink(missing_ok=True)
        log.warning("factory reset done (cache wiped: %s)", body.include_cache)
        return {"ok": True}


    return router
