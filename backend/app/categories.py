"""User-defined category sets: validation and JSON storage (REQ-CAT-2)."""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .presets import PRESETS, PRESETS_BY_ID


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "category"


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    emoji: str | None = Field(default=None, max_length=8)
    prompts: list[str] = Field(default_factory=list, max_length=8)
    media: Literal["any", "image", "video"] = "any"  # which files this folder accepts

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
        cats.append({"id": cid, "name": c.name, "emoji": c.emoji or "📁", "prompts": c.prompts, "media": c.media})
    return {"id": set_id, "name": data.name.strip(), "description": data.description, "categories": cats, "custom": True}


class CategoryStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self, data: dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(self.path)

    def list(self) -> list[dict]:
        """User-created sets (preset overrides are not listed here)."""
        with self._lock:
            return [v for v in self._load().values() if not v.get("preset_override")]

    def presets(self) -> list[dict]:
        """Built-in presets, with the user's edits applied where a preset was modified."""
        with self._lock:
            saved = self._load()
        return [{**saved[p["id"]], "modified": True} if p["id"] in saved else p for p in PRESETS]

    def get(self, set_id: str) -> dict | None:
        with self._lock:
            saved = self._load().get(set_id)
        return saved or PRESETS_BY_ID.get(set_id)

    def upsert(self, set_id: str | None, data: CategorySetIn) -> dict:
        with self._lock:
            all_sets = self._load()
            if not set_id:
                base = "custom-" + slugify(data.name)
                set_id, n = base, 2
                while set_id in all_sets or set_id in PRESETS_BY_ID:
                    set_id = f"{base}-{n}"
                    n += 1
            d = to_set_dict(set_id, data)
            if set_id in PRESETS_BY_ID:  # editing a built-in preset = saving an override
                d["custom"] = False
                d["preset_override"] = True
                d["description"] = d["description"] or PRESETS_BY_ID[set_id].get("description")
            all_sets[set_id] = d
            self._save(all_sets)
            return d

    def delete(self, set_id: str) -> bool:
        """Delete a custom set, or reset a modified preset to its default."""
        with self._lock:
            all_sets = self._load()
            if set_id not in all_sets:
                return False
            del all_sets[set_id]
            self._save(all_sets)
            return True


def all_presets() -> list[dict]:
    return PRESETS
