"""Catalog HTTP routes."""
from __future__ import annotations

from fastapi import HTTPException
from app.catalog.categories import CategorySetIn
from app.catalog.presets import RECIPES
from fastapi import APIRouter
from app.api.context import Runtime


def create_router(ctx: Runtime) -> APIRouter:
    router = APIRouter(tags=["catalog"])
    store = ctx.store

    @router.get("/api/presets")
    def presets():
        return store.presets()


    @router.get("/api/category-sets")
    def list_sets():
        return store.list()


    @router.post("/api/category-sets", status_code=201)
    def create_set(body: CategorySetIn):
        return store.upsert(None, body)


    @router.put("/api/category-sets/{set_id}")
    def update_set(set_id: str, body: CategorySetIn):
        try:
            return store.upsert(set_id, body)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc


    @router.delete("/api/category-sets/{set_id}", status_code=204)
    def delete_set(set_id: str):
        """Deletes a custom set, or resets an edited preset to its default."""
        if not store.delete(set_id):
            raise HTTPException(404, "not found")


    @router.get("/api/recipes")
    def recipes():
        return RECIPES


    return router
