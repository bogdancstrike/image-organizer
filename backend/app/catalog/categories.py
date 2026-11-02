"""User-defined category sets: validation and JSON storage (REQ-CAT-2)."""
from __future__ import annotations

import re

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.catalog.presets import PRESETS, PRESETS_BY_ID


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "category"


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    emoji: str | None = Field(default=None, max_length=8)
    prompts: list[str] = Field(default_factory=list, max_length=8)
    media: Literal["any", "image", "video"] = "any"  # which files this folder accepts
    ai_hint: str | None = Field(default=None, max_length=300)  # extra instruction for the AI about this folder

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        if re.search(r'[/\\:*?"<>|]', v):
            raise ValueError("name contains a character not allowed in folder names")
        return v

    @field_validator("prompts")
    @classmethod
    def _clean_prompts(cls, v: list[str]) -> list[str]:
        return [p.strip()[:200] for p in v if p and p.strip()]


class CategorySetIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=200)
    categories: list[CategoryIn] = Field(min_length=1, max_length=40)

    @field_validator("categories")
    @classmethod
    def _unique(cls, v: list[CategoryIn]) -> list[CategoryIn]:
        seen: set[str] = set()
        for c in v:
            key = c.name.lower()
            if key in seen:
                raise ValueError(f'duplicate category name "{c.name}"')
            seen.add(key)
        return v


def to_set_dict(set_id: str, data: CategorySetIn) -> dict:
    cats, used = [], set()
    for c in data.categories:
        cid = slugify(c.name)
        base, n = cid, 2
        while cid in used:
            cid = f"{base}-{n}"
            n += 1
        used.add(cid)
        cats.append({"id": cid, "name": c.name, "emoji": c.emoji or "📁", "prompts": c.prompts, "media": c.media,
                     "ai_hint": (c.ai_hint or "").strip() or None})
    return {"id": set_id, "name": data.name.strip(), "description": data.description, "categories": cats, "custom": True}


SEED_VERSION = 2  # bump when built-in presets change; unedited seeded presets are refreshed


def default_hint(cat: dict) -> str:
    """Pre-filled AI hint for a preset folder: what belongs in it, from its descriptions."""
    prompts = [p for p in (cat.get("prompts") or [])][:3]
    what = "; ".join(prompts) if prompts else f"a photo of {cat['name'].lower()}"
    hint = f"Photos showing {what}."
    if cat.get("media") == "video":
        hint += " Videos only."
    return hint[:300]


def seeded_preset(p: dict) -> dict:
    cats = [{**c, "ai_hint": c.get("ai_hint") or default_hint(c)} for c in p["categories"]]
    return {**p, "categories": cats, "custom": False, "preset_override": True, "seeded": True}



def all_presets() -> list[dict]:
    return PRESETS
