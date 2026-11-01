"""Background sort jobs: scan → analyze → dedupe → categorize → plan, with a replayable event log."""
from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from . import classify
from .cache import AnalysisCache
from .categories import CategoryStore, slugify
from .config import Settings
from .dedupe import DupItem, find_duplicates
from .embedder import Embedder, normalize
from .llm import LLMClient, contact_sheet, load_thumb
from .media import Analysis, MediaError, decode
from .organizer import apply_plan
from .planner import DUPLICATES, UNSORTED, destination
from .presets import VOCABULARY
from .scanner import MediaFile, resolve_in_library, scan

log = logging.getLogger(__name__)

CHUNK = 48
TERMINAL = {"done", "error", "cancelled"}


class BusyError(RuntimeError):
    pass


@dataclass
class Job:
    id: str
    request: dict
    status: str = "running"  # running | done | error | cancelled | applied
    phase: str = "queued"
    events: list[dict] = field(default_factory=list)
    plan: list[dict] = field(default_factory=list)
    categories: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    usage: dict | None = None
    run_id: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    cancel_requested: bool = False
    cond: threading.Condition = field(default_factory=threading.Condition, repr=False)

    def emit(self, type: str, **data: Any) -> None:
        with self.cond:
            self.events.append({"seq": len(self.events), "type": type, **data})
            self.cond.notify_all()

    def events_since(self, seq: int, timeout: float = 10.0) -> list[dict]:
        with self.cond:
            if seq >= len(self.events) and self.status == "running":
                self.cond.wait(timeout)
            return self.events[seq:]

    @property
    def finished(self) -> bool:
        return self.status != "running"

    def snapshot(self, include_plan: bool = True) -> dict:
        d = {
            "id": self.id,
            "request": self.request,
            "status": self.status,
            "phase": self.phase,
            "categories": self.categories,
            "stats": self.stats,
            "warnings": self.warnings,
            "errors": self.errors,
            "usage": self.usage,
            "run_id": self.run_id,
            "error": self.error,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }
        if include_plan:
            d["plan"] = self.plan
        return d


class JobManager:
    def __init__(
        self,
        settings: Settings,
        embedder_factory: Callable[[], Embedder],
        store: CategoryStore,
        llm_factory: Callable[[], LLMClient | None] | None = None,
    ):
        self.s = settings
        self.embedder_factory = embedder_factory
        self.store = store
        self.llm_factory = llm_factory or (lambda: None)
        self.cache = AnalysisCache(settings.data_dir / "cache.db")
        self.jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ API
    def start(self, request: dict) -> Job:
        with self._lock:
            if any(j.status == "running" for j in self.jobs.values()):
                raise BusyError("a sort is already running")
            # validate early so the client gets a 4xx instead of a failed job
            resolve_in_library(self.s.library_root, request.get("source"))
            if request["strategy"] in ("preset", "custom") and not self.store.get(request.get("set_id") or ""):
                raise KeyError(f"unknown category set {request.get('set_id')!r}")
            job = Job(id=uuid.uuid4().hex[:12], request=request)
            self.jobs[job.id] = job
            # keep memory bounded
            for old in sorted(self.jobs.values(), key=lambda j: j.created_at)[:-20]:
                if old.finished:
                    self.jobs.pop(old.id, None)
        threading.Thread(target=self._run_safe, args=(job,), daemon=True, name=f"job-{job.id}").start()
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job or job.finished:
            return False
        job.cancel_requested = True
        return True

    def apply(self, job_id: str, mode: str) -> dict:
        job = self.jobs.get(job_id)
        if not job:
            raise KeyError(job_id)
        with self._lock:
            if job.status != "done":
                raise BusyError(f"job is {job.status}; only a finished, unapplied job can be applied")
            job.status = "applying"
        try:
            journal = apply_plan(
                self.s.library_root,
                [{"rel_path": p["rel_path"], "destination": p["destination"]} for p in job.plan],
                mode,
                self.s.journals_dir,
                job.id,
                job.request.get("source") or "",
            )
        except Exception:
            job.status = "done"
            raise
        job.status = "applied"
        job.run_id = journal["run_id"]
        return journal

    # ------------------------------------------------------------- pipeline
    def thumb_path(self, sha: str) -> Path:
        return self.s.thumbs_dir / sha[:2] / f"{sha}.webp"

    def _run_safe(self, job: Job) -> None:
        try:
            self._run(job)
            if job.cancel_requested:
                job.status = "cancelled"
                job.emit("cancelled")
            else:
                job.status = "done"
                job.phase = "done"
                job.emit("done", stats=job.stats, usage=job.usage, warnings=job.warnings)
        except Exception as exc:  # noqa: BLE001
            log.exception("job %s failed", job.id)
            job.error = str(exc)
            job.status = "error"
            job.emit("error", message=str(exc))
        finally:
            job.finished_at = time.time()
            with job.cond:
                job.cond.notify_all()

    def _phase(self, job: Job, phase: str) -> None:
        job.phase = phase
        job.emit("phase", phase=phase)

    def _analyze_one(self, f: MediaFile):
        key = str(f.path)
        try:
            cached = self.cache.get(key, f.size, f.mtime)
            if cached:
                analysis, emb = cached
                tp = self.thumb_path(analysis.sha256)
                if not tp.exists():
                    d = decode(f.path, f.kind, f.mtime)
                    tp.parent.mkdir(parents=True, exist_ok=True)
                    tp.write_bytes(d.thumb)
                return ("cached", f, analysis, emb)
            d = decode(f.path, f.kind, f.mtime)
            tp = self.thumb_path(d.analysis.sha256)
            tp.parent.mkdir(parents=True, exist_ok=True)
            tp.write_bytes(d.thumb)
            return ("new", f, d, None)
        except (MediaError, OSError) as exc:
            return ("error", f, str(exc), None)
        except Exception as exc:  # noqa: BLE001 - decoder bugs on exotic files
            return ("error", f, f"unexpected: {exc}", None)

    def _run(self, job: Job) -> None:
        req = job.request
        opts = req.get("options", {})
        root = self.s.library_root
        source = resolve_in_library(root, req.get("source"))
        source_rel = "" if source == root else source.relative_to(root).as_posix()

        # 1. scan
        self._phase(job, "scanning")
        files = scan(root, source, self.s.output_dir_name)
        n_img = sum(f.kind == "image" for f in files)
        job.stats = {"total": len(files), "photos": n_img, "videos": len(files) - n_img,
                     "analyzed": 0, "folders": 0, "duplicates": 0, "errors": 0, "embedded": 0}
        job.emit("scanned", total=len(files), photos=n_img, videos=len(files) - n_img,
                 source=source_rel, source_name=source.name if source_rel else "Library")

        # 2. analyze
        self._phase(job, "analyzing")
        embedder = self.embedder_factory() if files else None
        results: dict[str, tuple[MediaFile, Analysis, np.ndarray]] = {}
        with ThreadPoolExecutor(max_workers=self.s.workers) as ex:
            for start in range(0, len(files), CHUNK):
                if job.cancel_requested:
                    return
                chunk = files[start : start + CHUNK]
                pending: list[tuple[MediaFile, Any]] = []
                for kind, f, payload, emb in ex.map(self._analyze_one, chunk):
                    if kind == "error":
                        job.errors.append({"rel_path": f.rel_path, "error": payload})
                        job.stats["errors"] += 1
                        job.emit("file_error", id=f.id, rel_path=f.rel_path, error=payload)
                        continue
                    analysis = payload if kind == "cached" else payload.analysis
                    job.emit("file", id=f.id, kind=f.kind, rel_path=f.rel_path, name=f.name,
                             thumb=f"/api/thumbs/{analysis.sha256}")
                    if kind == "cached":
                        results[f.id] = (f, analysis, emb)
                    else:
                        pending.append((f, payload))
                if pending:
                    frames, owners = [], []
                    for i, (_, d) in enumerate(pending):
                        frames.extend(d.frames)
                        owners.extend([i] * len(d.frames))
                    vecs = embedder.embed_images(frames)
                    owners_arr = np.array(owners)
                    for i, (f, d) in enumerate(pending):
                        emb = normalize(vecs[owners_arr == i].mean(axis=0))
                        self.cache.put(str(f.path), f.size, f.mtime, d.analysis, emb)
                        results[f.id] = (f, d.analysis, emb)
                    job.stats["embedded"] += len(pending)
                job.stats["analyzed"] = len(results) + job.stats["errors"]
                job.emit("progress", analyzed=job.stats["analyzed"], total=len(files))

        ordered = [results[f.id] for f in files if f.id in results]

        # 3. duplicates
        self._phase(job, "deduplicating")
        dup_items = [
            DupItem(f.id, f.kind, a.sha256, a.phash, (a.width or 0) * (a.height or 0), f.size, a.captured_at,
                    f.rel_path, a.duration, e)
            for f, a, e in ordered
        ]
        dup_map = find_duplicates(dup_items, near=opts.get("near_duplicates", True),
                                  max_distance=int(opts.get("near_dup_distance", 4)))
        job.stats["duplicates"] = len(dup_map)
        job.emit("stats", **job.stats)

        # 4. categorize
        self._phase(job, "categorizing")
        keep = [(f, a, e) for f, a, e in ordered if f.id not in dup_map]
        assignment, categories = self._categorize(job, keep, embedder)
        if job.cancel_requested:
            return

        # 5. plan
        cats_by_id = {c["id"]: c for c in categories}
        if any(cid is None for cid, _, _ in assignment.values()):
            cats_by_id[UNSORTED["id"]] = dict(UNSORTED)
        if dup_map:
            cats_by_id[DUPLICATES["id"]] = dict(DUPLICATES)
        split = opts.get("split_media", True)
        plan = []
        for f, a, e in ordered:
            if f.id in dup_map:
                cid, conf, src = DUPLICATES["id"], 1.0, "duplicate"
            else:
                cid, conf, src = assignment[f.id]
                cid = cid or UNSORTED["id"]
            cat = cats_by_id[cid]
            plan.append({
                "file_id": f.id, "rel_path": f.rel_path, "name": f.name, "kind": f.kind,
                "thumb": f"/api/thumbs/{a.sha256}", "category_id": cid, "category": cat["name"],
                "confidence": round(float(conf), 4), "source": src,
                "destination": destination(source_rel, self.s.output_dir_name, f.kind, cat, split),
                "duplicate_of": dup_map.get(f.id),
            })
        counts: dict[str, dict[str, int]] = {}
        for p in plan:
            c = counts.setdefault(p["category_id"], {"photos": 0, "videos": 0})
            c["photos" if p["kind"] == "image" else "videos"] += 1
        order = [c["id"] for c in categories] + [UNSORTED["id"], DUPLICATES["id"]]
        job.categories = [
            {**cats_by_id[cid], **counts[cid]} for cid in order if cid in counts and cid in cats_by_id
        ]
        job.plan = plan
        job.stats["folders"] = len({p["destination"] for p in plan if p["category_id"] != DUPLICATES["id"]})
        job.emit("categories", categories=job.categories)
        shuffled = list(plan)
        random.Random(job.id).shuffle(shuffled)
        for p in shuffled:
            job.emit("assign", id=p["file_id"], category_id=p["category_id"], kind=p["kind"])
        job.emit("stats", **job.stats)

    # --------------------------------------------------------- strategies
    def _categorize(self, job: Job, keep, embedder) -> tuple[dict, list[dict]]:
        req, opts = job.request, job.request.get("options", {})
        strategy = req["strategy"]
        assignment: dict[str, tuple[str | None, float, str]] = {}
        if not keep:
            return assignment, []
        embs = np.vstack([e for _, _, e in keep]) if keep else np.zeros((0, 512), np.float32)

        if strategy == "date":
            gran = opts.get("date_granularity", "month")
            names = [classify.date_category(a.captured_at, gran) for _, a, _ in keep]
            uniq = sorted(set(names))
            cats = [{"id": "d-" + slugify(n), "name": n, "emoji": "📅"} for n in uniq]
            ids = {n: c["id"] for n, c in zip(uniq, cats)}
            for (f, _, _), n in zip(keep, names):
                assignment[f.id] = (ids[n], 1.0, "date")
            return assignment, cats

        if strategy == "auto":
            labels, cents = classify.choose_k(embs, int(opts.get("max_clusters", 12)))
            names = self._name_clusters(job, keep, embs, labels, cents, embedder)
            cats: list[dict] = []
            by_name: dict[str, str] = {}
            label_to_cat: dict[int, str] = {}
            for ci, (name, emoji) in enumerate(names):
                key = name.lower()
                if key not in by_name:
                    cid = slugify(name)
                    while any(c["id"] == cid for c in cats):
                        cid += "-x"
                    by_name[key] = cid
                    cats.append({"id": cid, "name": name, "emoji": emoji or "📁"})
                label_to_cat[ci] = by_name[key]
            for i, (f, _, e) in enumerate(keep):
                ci = int(labels[i])
                assignment[f.id] = (label_to_cat[ci], float(e @ cents[ci]), "cluster")
            return assignment, cats

        # preset / custom
        cset = self.store.get(req.get("set_id") or "")
        if not cset:
            raise KeyError("category set not found")
        cats = [dict(c) for c in cset["categories"]]
        res = classify.classify_with_set(
            embs, [a.is_screenshot for _, a, _ in keep], cats, embedder, float(opts.get("min_confidence", 0.3))
        )
        for (f, _, _), r in zip(keep, res):
            assignment[f.id] = r
        if opts.get("ai_assist"):
            self._assist(job, keep, assignment, cats, int(opts.get("ai_max_files", 200)))
        return assignment, cats

    def _llm(self, job: Job) -> LLMClient | None:
        try:
            return self.llm_factory()
        except Exception as exc:  # noqa: BLE001
            job.warnings.append(f"AI unavailable: {exc}")
            return None

    def _name_clusters(self, job, keep, embs, labels, cents, embedder) -> list[tuple[str, str]]:
        vocab_names = classify.name_by_vocabulary(cents, embedder)
        llm = self._llm(job)
        if not llm:
            return vocab_names
        try:
            reps = classify.representatives(embs, labels, cents)
            sheets = [contact_sheet([self.thumb_path(keep[i][1].sha256) for i in r]) for r in reps]
            ai = llm.name_clusters(sheets)
            job.usage = dict(llm.usage, model=llm.model)
            return [(n, e) if n else vocab_names[i] for i, (n, e) in enumerate(ai)]
        except Exception as exc:  # noqa: BLE001 - REQ-CAT-9 graceful fallback
            log.warning("cluster naming failed: %s", exc)
            job.warnings.append(f"AI naming failed, used local names ({type(exc).__name__})")
            job.emit("warning", message=job.warnings[-1])
            return vocab_names

    def _assist(self, job, keep, assignment, cats, max_files: int) -> None:
        unsure = [(f, a) for f, a, _ in keep if assignment[f.id][0] is None][:max_files]
        if not unsure:
            return
        llm = self._llm(job)
        if not llm:
            job.warnings.append("AI assist is on but no OpenAI key is configured")
            return
        thumbs, owners = [], []
        for f, a in unsure:
            t = load_thumb(self.thumb_path(a.sha256))
            if t is not None:
                thumbs.append(t)
                owners.append(f)
        try:
            labels = llm.assist(thumbs, [c["name"] for c in cats])
        except Exception as exc:  # noqa: BLE001
            log.warning("assist failed: %s", exc)
            job.warnings.append(f"AI assist failed, kept local results ({type(exc).__name__})")
            job.emit("warning", message=job.warnings[-1])
            return
        finally:
            job.usage = dict(llm.usage, model=llm.model)
        name_to_id = {c["name"].lower(): c["id"] for c in cats}
        for f, label in zip(owners, labels):
            cid = name_to_id.get(label.lower())
            if cid:
                assignment[f.id] = (cid, assignment[f.id][1], "ai")
