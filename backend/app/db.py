"""App database (SQLite, data/app.db): run history, UI settings and per-sort statistics.

Category sets live in the same file (see categories.CategoryStore). Everything is JSON-in-SQLite: simple,
transactional, and easy to back up (one file).
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path


class AppDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, created_at TEXT, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS job_stats (job_id TEXT PRIMARY KEY, finished_at REAL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, updated_at REAL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS face_refs (id TEXT PRIMARY KEY, created_at REAL, data TEXT NOT NULL);
            """
        )
        self._db.commit()
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- runs (History)
    def upsert_run(self, summary: dict) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO runs (run_id, created_at, data) VALUES (?,?,?)",
                (summary["run_id"], summary.get("created_at") or "", json.dumps(summary)),
            )
            self._db.commit()

    def runs(self, limit: int = 200) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT data FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def has_runs(self) -> bool:
        with self._lock:
            return self._db.execute("SELECT 1 FROM runs LIMIT 1").fetchone() is not None

    # ---------------------------------------------------------------- settings
    def get_setting(self, key: str, default=None):
        with self._lock:
            row = self._db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(self, key: str, value) -> None:
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, json.dumps(value)))
            self._db.commit()

    def wipe(self) -> None:
        """Factory reset: history, settings, statistics, saved sorts and reference faces."""
        with self._lock:
            for table in ("runs", "settings", "job_stats", "jobs", "face_refs"):
                self._db.execute(f"DELETE FROM {table}")  # noqa: S608 - fixed table names
            self._db.commit()

    # ---------------------------------------------------------------- finished sorts (survive refreshes & restarts)
    def save_job(self, snapshot: dict, keep: int = 20) -> None:
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO jobs (id, updated_at, data) VALUES (?,?,?)",
                             (snapshot["id"], time.time(), json.dumps(snapshot)))
            self._db.execute("DELETE FROM jobs WHERE id NOT IN (SELECT id FROM jobs ORDER BY updated_at DESC LIMIT ?)", (keep,))
            self._db.commit()

    def load_job(self, job_id: str) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT data FROM jobs WHERE id=?", (job_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def job_for_run(self, run_id: str) -> dict | None:
        with self._lock:
            rows = self._db.execute("SELECT data FROM jobs ORDER BY updated_at DESC").fetchall()
        for (d,) in rows:
            j = json.loads(d)
            if j.get("run_id") == run_id:
                return j
        return None

    # ---------------------------------------------------------------- reference faces ("find this person")
    def add_face_ref(self, ref: dict) -> None:
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO face_refs (id, created_at, data) VALUES (?,?,?)", (ref["id"], time.time(), json.dumps(ref)))
            self._db.commit()

    def face_refs(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT data FROM face_refs ORDER BY created_at DESC").fetchall()
        return [json.loads(r[0]) for r in rows]

    def get_face_ref(self, ref_id: str) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT data FROM face_refs WHERE id=?", (ref_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def delete_face_ref(self, ref_id: str) -> bool:
        with self._lock:
            n = self._db.execute("DELETE FROM face_refs WHERE id=?", (ref_id,)).rowcount
            self._db.commit()
        return n > 0

    # ---------------------------------------------------------------- statistics
    def add_job_stats(self, job_id: str, data: dict) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO job_stats (job_id, finished_at, data) VALUES (?,?,?)",
                (job_id, data.get("finished_at") or time.time(), json.dumps(data)),
            )
            self._db.commit()

    def job_stats(self, limit: int = 500) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT data FROM job_stats ORDER BY finished_at DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(r[0]) for r in rows]


OUTCOMES = ("applied", "undone", "not_applied", "cancelled", "failed")


def history(db: "AppDB", outcome: str | None = None, limit: int = 20, offset: int = 0) -> dict:
    """Every sort, accepted or not: what was sorted, how, how long, and what happened to the plan."""
    runs = db.runs(limit=5000)
    by_job = {r.get("job_id"): r for r in runs if r.get("job_id")}
    with db._lock:
        saved = {i: json.loads(d) for i, d in db._db.execute("SELECT id, data FROM jobs").fetchall()}
    items: list[dict] = []
    seen_runs: set[str] = set()
    for s in db.job_stats(limit=5000):
        run = by_job.get(s["job_id"])
        if run:
            seen_runs.add(run["run_id"])
        st = s.get("status")
        out = ("failed" if st == "error" else "cancelled" if st == "cancelled" else
               (run["status"] if run and run.get("status") in ("applied", "undone") else "not_applied"))
        snap = saved.get(s["job_id"]) or {}
        cats = sorted(({"name": c.get("name"), "count": (c.get("photos") or 0) + (c.get("videos") or 0)}
                       for c in snap.get("categories") or []), key=lambda c: -c["count"])
        items.append({**{k: s.get(k) for k in ("job_id", "finished_at", "source", "strategy", "model", "files", "photos", "videos",
                                                 "embedded", "duplicates", "folders", "wall", "phases", "usage")},
                      "outcome": out, "run": run, "categories": cats[:12], "reopen": bool(snap) and out in ("not_applied", "undone")})
    for r in runs:  # applies made before statistics existed
        if r["run_id"] in seen_runs:
            continue
        ts = r.get("created_at") or ""
        try:
            from datetime import datetime
            t = datetime.fromisoformat(ts).timestamp() if ts else 0
        except ValueError:
            t = 0
        items.append({"job_id": r.get("job_id"), "finished_at": t, "source": r.get("source"), "strategy": None, "model": None,
                      "files": r.get("moved"), "outcome": r.get("status") if r.get("status") in ("applied", "undone") else "applied",
                      "run": r, "categories": [], "reopen": False})
    items.sort(key=lambda x: -(x.get("finished_at") or 0))
    counts = {o: sum(1 for i in items if i["outcome"] == o) for o in OUTCOMES}
    counts["all"] = len(items)
    rows = [i for i in items if not outcome or outcome == "all" or i["outcome"] == outcome]
    return {"items": rows[offset: offset + limit], "total": len(rows), "counts": counts, "limit": limit, "offset": offset}


def summarize(stats: list[dict], runs: list[dict]) -> dict:
    """Aggregates for the Statistics tab."""
    done = [s for s in stats if s.get("status") == "done"]
    total_files = sum(s.get("files", 0) for s in done)
    total_time = sum(s.get("wall", 0.0) for s in done)
    phase_totals: dict[str, float] = {}
    for s in done:
        for k, v in (s.get("phases") or {}).items():
            phase_totals[k] = phase_totals.get(k, 0.0) + v
    by_strategy: dict[str, int] = {}
    by_model: dict[str, int] = {}
    for s in done:
        by_strategy[s.get("strategy", "?")] = by_strategy.get(s.get("strategy", "?"), 0) + 1
        by_model[s.get("model", "clip")] = by_model.get(s.get("model", "clip"), 0) + 1
    tokens = sum((s.get("usage") or {}).get("input_tokens", 0) + (s.get("usage") or {}).get("output_tokens", 0) for s in done)
    return {
        "sorts": len(done),
        "failed_sorts": len([s for s in stats if s.get("status") == "error"]),
        "files_processed": total_files,
        "files_analyzed": sum(s.get("embedded", 0) for s in done),
        "processing_seconds": round(total_time, 2),
        "avg_files_per_second": round(total_files / total_time, 1) if total_time else 0,
        "avg_seconds_per_sort": round(total_time / len(done), 2) if done else 0,
        "phase_seconds": {k: round(v, 2) for k, v in sorted(phase_totals.items(), key=lambda x: -x[1])},
        "by_strategy": by_strategy,
        "by_model": by_model,
        "applies": len([r for r in runs if r.get("status") in ("applied", "undone")]),
        "photos_organized": sum(r.get("moved", 0) for r in runs if r.get("status") == "applied"),
        "ai_tokens": tokens,
        "recent": [
            {k: s.get(k) for k in ("job_id", "finished_at", "strategy", "model", "files", "photos", "videos", "embedded",
                                   "duplicates", "folders", "wall", "phases", "source", "status")}
            for s in stats[:60]
        ],
    }
