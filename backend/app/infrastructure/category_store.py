"""SQLite category repository and legacy data migration."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from app.catalog.presets import PRESETS, PRESETS_BY_ID
from app.catalog.categories import CategorySetIn, SEED_VERSION, seeded_preset, to_set_dict, slugify

class CategoryStore:
    """Category sets in SQLite (data/app.db). Built-in presets are seeded on first start (with AI hints);
    users can edit them (marked as modified) and reset them to the seeded default."""

    def __init__(self, path: Path):
        # `path` may be the legacy JSON file; the database lives next to it
        self.legacy = path if path.suffix == ".json" else None
        self.db_path = path.with_name("app.db") if path.suffix == ".json" else path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("CREATE TABLE IF NOT EXISTS category_sets (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
        self._db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        self._db.commit()
        self._migrate_legacy()
        self.seed()

    # ---- low level
    def _all(self) -> dict[str, dict]:
        rows = self._db.execute("SELECT id, data FROM category_sets").fetchall()
        return {i: json.loads(d) for i, d in rows}

    def _put(self, d: dict) -> None:
        self._db.execute("INSERT OR REPLACE INTO category_sets (id, data) VALUES (?, ?)", (d["id"], json.dumps(d, ensure_ascii=False)))

    def _migrate_legacy(self) -> None:
        if not (self.legacy and self.legacy.exists()):
            return
        try:
            data = json.loads(self.legacy.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        with self._lock:
            for d in data.values():
                self._put(d)
            self._db.commit()
        self.legacy.rename(self.legacy.with_suffix(".json.migrated"))

    def wipe(self) -> None:
        """Factory reset: drop every custom set and edited preset, then re-seed the built-in presets."""
        with self._lock:
            self._db.execute("DELETE FROM category_sets")
            self._db.execute("DELETE FROM meta WHERE key='seed_version'")
            self._db.commit()
        self.seed()

    def seed(self) -> int:
        """Insert built-in presets that are missing (or refresh unedited ones after a preset update)."""
        with self._lock:
            row = self._db.execute("SELECT value FROM meta WHERE key='seed_version'").fetchone()
            version = int(row[0]) if row else 0
            saved = self._all()
            n = 0
            for p in PRESETS:
                cur = saved.get(p["id"])
                if cur is None or (version < SEED_VERSION and cur.get("seeded")):
                    self._put(seeded_preset(p))
                    n += 1
            self._db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('seed_version', ?)", (str(SEED_VERSION),))
            self._db.commit()
            return n

    # ---- API
    def list(self) -> list[dict]:
        """User-created sets (presets are listed by presets())."""
        with self._lock:
            return [v for v in self._all().values() if not v.get("preset_override")]

    def presets(self) -> list[dict]:
        with self._lock:
            saved = self._all()
        out = []
        for p in PRESETS:
            d = saved.get(p["id"]) or seeded_preset(p)
            out.append({**d, "modified": not d.get("seeded", False)})
        return out

    def get(self, set_id: str) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT data FROM category_sets WHERE id=?", (set_id,)).fetchone()
        if row:
            return json.loads(row[0])
        return seeded_preset(PRESETS_BY_ID[set_id]) if set_id in PRESETS_BY_ID else None

    def upsert(self, set_id: str | None, data: CategorySetIn) -> dict:
        with self._lock:
            existing = self._all()
            if not set_id:
                base = "custom-" + slugify(data.name)
                set_id, n = base, 2
                while set_id in existing or set_id in PRESETS_BY_ID:
                    set_id = f"{base}-{n}"
                    n += 1
            d = to_set_dict(set_id, data)
            if set_id in PRESETS_BY_ID:  # editing a built-in preset: no longer the seeded default
                d.update(custom=False, preset_override=True, seeded=False)
                d["description"] = d["description"] or PRESETS_BY_ID[set_id].get("description")
            self._put(d)
            self._db.commit()
            return d

    def delete(self, set_id: str) -> bool:
        """Delete a custom set, or reset a built-in preset to its seeded default (it stays in the database)."""
        with self._lock:
            row = self._db.execute("SELECT data FROM category_sets WHERE id=?", (set_id,)).fetchone()
            if set_id in PRESETS_BY_ID:
                if row is None or json.loads(row[0]).get("seeded"):
                    return False
                self._put(seeded_preset(PRESETS_BY_ID[set_id]))
            else:
                if row is None:
                    return False
                self._db.execute("DELETE FROM category_sets WHERE id=?", (set_id,))
            self._db.commit()
            return True

