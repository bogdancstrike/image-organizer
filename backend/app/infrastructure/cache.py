"""SQLite analysis cache keyed by (path, size, mtime). Spec: REQ-ANL-6."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

import numpy as np

from app.media.decoding import Analysis


class AnalysisCache:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, size INTEGER, mtime REAL, meta TEXT, emb BLOB)"
        )
        self._db.execute("CREATE TABLE IF NOT EXISTS quality (path TEXT PRIMARY KEY, size INTEGER, mtime REAL, data TEXT)")
        self._lock = threading.Lock()

    def get_json(self, table: str, path: str, size: int, mtime: float) -> dict | list | None:
        with self._lock:
            self._db.execute(f"CREATE TABLE IF NOT EXISTS {table} (path TEXT PRIMARY KEY, size INTEGER, mtime REAL, data TEXT)")
            row = self._db.execute(f"SELECT size, mtime, data FROM {table} WHERE path=?", (path,)).fetchone()
        if not row or row[0] != size or abs(row[1] - mtime) > 1e-6:
            return None
        return json.loads(row[2])

    def put_json(self, table: str, path: str, size: int, mtime: float, data) -> None:
        with self._lock:
            self._db.execute(f"CREATE TABLE IF NOT EXISTS {table} (path TEXT PRIMARY KEY, size INTEGER, mtime REAL, data TEXT)")
            self._db.execute(f"INSERT OR REPLACE INTO {table} (path, size, mtime, data) VALUES (?,?,?,?)",
                             (path, size, mtime, json.dumps(data)))
            self._db.commit()

    def get_quality(self, path: str, size: int, mtime: float) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT size, mtime, data FROM quality WHERE path=?", (path,)).fetchone()
        if not row or row[0] != size or abs(row[1] - mtime) > 1e-6:
            return None
        return json.loads(row[2])

    def put_quality(self, path: str, size: int, mtime: float, data: dict) -> None:
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO quality (path, size, mtime, data) VALUES (?,?,?,?)",
                             (path, size, mtime, json.dumps(data)))
            self._db.commit()

    def get(self, path: str, size: int, mtime: float) -> tuple[Analysis, np.ndarray] | None:
        with self._lock:
            row = self._db.execute("SELECT size, mtime, meta, emb FROM files WHERE path=?", (path,)).fetchone()
        if not row or row[0] != size or abs(row[1] - mtime) > 1e-6 or row[3] is None:
            return None
        return Analysis.from_dict(json.loads(row[2])), np.frombuffer(row[3], dtype=np.float32).copy()

    def put(self, path: str, size: int, mtime: float, analysis: Analysis, emb: np.ndarray) -> None:
        blob = np.asarray(emb, dtype=np.float32).tobytes()
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO files (path, size, mtime, meta, emb) VALUES (?,?,?,?,?)",
                (path, size, mtime, json.dumps(analysis.to_dict()), blob),
            )
            self._db.commit()

    def embedding_signature(self) -> tuple:
        with self._lock:
            return self._db.execute("SELECT COUNT(*), COALESCE(MAX(rowid), 0) FROM files WHERE emb IS NOT NULL").fetchone()

    def embedding_rows(self) -> list[tuple]:
        with self._lock:
            return self._db.execute("SELECT path, meta, emb FROM files WHERE emb IS NOT NULL").fetchall()

    def auxiliary_rows(self, table: str, current: bool = False) -> list[tuple]:
        if table not in {"tags", "ocr", "quality", "faceid", "geo", "aesthetics"}:
            raise ValueError("unknown auxiliary cache")
        with self._lock:
            exists = self._db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if not exists:
                return []
            if current:
                return self._db.execute(f"SELECT t.path,t.data,t.size,t.mtime FROM {table} t JOIN files f ON f.path=t.path AND f.size=t.size AND ABS(f.mtime-t.mtime)<0.000001").fetchall()
            return self._db.execute(f"SELECT path,data,size,mtime FROM {table}").fetchall()

    def copy_paths(self, pairs: list[tuple[str, str]]) -> None:
        """Preserve analysis at Apply destinations. Original entries support Undo without re-inference."""
        with self._lock:
            tables = {r[0] for r in self._db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for src, dst in pairs:
                try:
                    stat = Path(dst).stat()
                except OSError:
                    continue
                self._db.execute("INSERT OR REPLACE INTO files SELECT ?,size,mtime,meta,emb FROM files WHERE path=? AND size=? AND ABS(mtime-?)<0.000001",
                                 (dst, src, stat.st_size, stat.st_mtime))
                for table in ("tags", "quality", "ocr", "faceid", "geo", "aesthetics"):
                    if table in tables:
                        self._db.execute(f"INSERT OR REPLACE INTO {table} SELECT ?,size,mtime,data FROM {table} WHERE path=? AND size=? AND ABS(mtime-?)<0.000001",
                                         (dst, src, stat.st_size, stat.st_mtime))
            self._db.commit()

    def wipe(self) -> None:
        """Drop every cached analysis (embeddings, quality, OCR, faces, GPS…); files are re-analyzed on the next sort."""
        with self._lock:
            tables = [r[0] for r in self._db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in tables:
                self._db.execute(f'DELETE FROM "{t}"')  # noqa: S608 - names come from sqlite_master
            self._db.commit()
            self._db.execute("VACUUM")

    def close(self) -> None:
        with self._lock:
            self._db.close()
