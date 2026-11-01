"""Apply plans, write journals, undo runs (REQ-ORG-3..6)."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

FLUSH_EVERY = 25


def _unique(dst: Path) -> Path:
    if not dst.exists():
        return dst
    stem, suffix = dst.stem, dst.suffix
    n = 1
    while True:
        cand = dst.with_name(f"{stem} ({n}){suffix}")
        if not cand.exists():
            return cand
        n += 1


def _write_journal(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(path)


def _inside(root: Path, p: Path) -> bool:
    p = p.resolve()
    return p == root or root in p.parents


def apply_plan(
    library_root: Path,
    items: list[dict],
    mode: str,
    journals_dir: Path,
    job_id: str,
    source: str,
    on_progress=None,
) -> dict:
    """items: [{rel_path, destination}] (library-relative). Returns the journal dict."""
    if mode not in ("move", "copy"):
        raise ValueError("mode must be move or copy")
    root = library_root.resolve()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    jpath = journals_dir / f"{run_id}.json"
    journal = {
        "run_id": run_id,
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "source": source,
        "status": "applying",
        "ops": [],
        "created_dirs": [],
        "failed": [],
        "skipped": 0,
    }
    _write_journal(jpath, journal)
    created_dirs: list[str] = []

    for n, it in enumerate(items, 1):
        src = root / it["rel_path"]
        dst_dir = root / it["destination"]
        try:
            if not _inside(root, dst_dir) or not _inside(root, src):
                raise ValueError("path outside library")
            if not src.exists():
                raise FileNotFoundError("source missing")
            if src.parent.resolve() == dst_dir.resolve():
                journal["skipped"] += 1
                continue
            # record dirs we create (outermost first) for undo cleanup
            missing = []
            d = dst_dir
            while not d.exists():
                missing.append(d)
                d = d.parent
            dst_dir.mkdir(parents=True, exist_ok=True)
            created_dirs.extend(p.relative_to(root).as_posix() for p in reversed(missing))
            dst = _unique(dst_dir / src.name)
            op = {"src": it["rel_path"], "dst": dst.relative_to(root).as_posix()}
            if mode == "move":
                shutil.move(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))
                st = dst.stat()
                op["size"], op["mtime"] = st.st_size, st.st_mtime
            journal["ops"].append(op)
        except Exception as exc:  # noqa: BLE001 - record and continue (REQ-ORG-4)
            journal["failed"].append({"src": it["rel_path"], "error": str(exc)})
        if n % FLUSH_EVERY == 0:
            journal["created_dirs"] = created_dirs
            _write_journal(jpath, journal)
        if on_progress:
            on_progress(n, len(items))

    journal["created_dirs"] = created_dirs
    journal["status"] = "applied"
    journal["applied_at"] = datetime.now(timezone.utc).isoformat()
    _write_journal(jpath, journal)
    return journal


def undo_run(library_root: Path, journals_dir: Path, run_id: str) -> dict:
    root = library_root.resolve()
    jpath = journals_dir / f"{run_id}.json"
    if not jpath.exists() or "/" in run_id or ".." in run_id:
        raise FileNotFoundError(run_id)
    journal = json.loads(jpath.read_text("utf-8"))
    if journal.get("status") == "undone":
        return journal
    restored, problems = 0, []
    for op in reversed(journal.get("ops", [])):
        src, dst = root / op["src"], root / op["dst"]
        try:
            if not dst.exists():
                problems.append({"file": op["dst"], "error": "no longer exists"})
                continue
            if journal["mode"] == "move":
                if src.exists():
                    problems.append({"file": op["src"], "error": "original path is occupied"})
                    continue
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), str(src))
            else:
                st = dst.stat()
                if st.st_size != op.get("size") or abs(st.st_mtime - op.get("mtime", 0)) > 1e-3:
                    problems.append({"file": op["dst"], "error": "copy was modified; kept"})
                    continue
                dst.unlink()
            restored += 1
        except OSError as exc:
            problems.append({"file": op["dst"], "error": str(exc)})
    for d in sorted(set(journal.get("created_dirs", [])), key=lambda s: s.count("/"), reverse=True):
        p = root / d
        try:
            if p.is_dir() and _inside(root, p) and p != root:
                # remove OS junk so "empty" means empty to the user
                for junk in (".DS_Store", "Thumbs.db"):
                    (p / junk).unlink(missing_ok=True)
                os.rmdir(p)
        except OSError:
            pass
    journal["status"] = "undone"
    journal["undone_at"] = datetime.now(timezone.utc).isoformat()
    journal["undo"] = {"restored": restored, "problems": problems}
    _write_journal(jpath, journal)
    return journal


def list_runs(journals_dir: Path) -> list[dict]:
    if not journals_dir.exists():
        return []
    runs = []
    for p in journals_dir.glob("*.json"):
        try:
            j = json.loads(p.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        runs.append({
            "run_id": j["run_id"],
            "job_id": j.get("job_id"),
            "created_at": j.get("created_at"),
            "mode": j.get("mode"),
            "source": j.get("source"),
            "status": j.get("status"),
            "moved": len(j.get("ops", [])),
            "failed": len(j.get("failed", [])),
            "undo": j.get("undo"),
        })
    runs.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return runs
