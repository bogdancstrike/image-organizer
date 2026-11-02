"""Background sort jobs: scan → analyze → dedupe → categorize → plan, with a replayable event log."""
from __future__ import annotations

import hashlib
import logging
import random
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from . import classify
from .rules import validate_rules
from .cache import AnalysisCache
from .categories import CategoryStore, slugify
from .config import Settings
from .dedupe import DupItem, find_duplicates
from .embedder import Embedder, normalize
from .llm import LLMClient, contact_sheet, load_thumb
from .media import Analysis, MediaError, decode, load_for_quality
from .quality import QUALITY_VERSION, REASONS, Quality, QualityRules, analyze_image, find_bursts, get_face_analyzer, score, stars, summary, verdict
from .ocr import get_text_reader, text_category
from .organizer import apply_plan
from PIL import Image, ImageOps

from .library import add_places, locate_files, trips_for
from . import picks as picks_mod

from .people import (FaceID, assign_by_appearance, cluster_people, face_crop_webp, get_face_identifier, man_probability,
                     person_presence, text_bank)
from .planner import DUPLICATES, UNSORTED, destination
from .presets import FOCUS_FACETS, FOCUS_HINT, VOCABULARY
from .scanner import MediaFile, resolve_in_library, scan

log = logging.getLogger(__name__)

CHUNK = 48
TRASH_DIR = ".aio-trash"  # recoverable "delete": hidden, skipped by scans, emptied explicitly from History
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
    context: dict | None = None
    run_id: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    cancel_requested: bool = False
    phase_times: list = field(default_factory=list)  # [(phase, started_at)]
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
            "context": self.context,
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
        self.cache = AnalysisCache(settings.data_dir / "cache.db")  # CLIP embeddings + model-agnostic tables
        self._caches = {"clip": self.cache}
        self.jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def cache_for(self, model: str) -> AnalysisCache:
        """Embeddings differ per model, so each model has its own cache file."""
        if model not in self._caches:
            self._caches[model] = AnalysisCache(self.s.data_dir / f"cache-{model}.db")
        return self._caches[model]

    def embedder_for(self, model: str):
        try:
            return self.embedder_factory(model)
        except TypeError:  # simple factories (tests) take no argument
            return self.embedder_factory()

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
        """In memory, or a finished sort restored from the database (e.g. after a restart)."""
        job = self.jobs.get(job_id)
        if job is None and getattr(self, "db", None):
            d = self.db.load_job(job_id)
            if d:
                job = Job(id=d["id"], request=d["request"], status=d["status"], phase=d.get("phase", "done"),
                          plan=d.get("plan") or [], categories=d.get("categories") or [], stats=d.get("stats") or {},
                          warnings=d.get("warnings") or [], errors=d.get("errors") or [], usage=d.get("usage"),
                          context=d.get("context"), run_id=d.get("run_id"), error=d.get("error"),
                          created_at=d.get("created_at") or time.time(), finished_at=d.get("finished_at"))
                with self._lock:
                    self.jobs.setdefault(job_id, job)
                    job = self.jobs[job_id]
        return job

    def _persist(self, job: Job) -> None:
        if getattr(self, "db", None) and job.status in ("done", "applied"):
            try:
                self.db.save_job(job.snapshot(include_plan=True))
            except Exception as exc:  # noqa: BLE001 - persistence must never break a sort
                log.warning("could not save job %s: %s", job.id, exc)

    def factory_reset(self, include_cache: bool) -> None:
        with self._lock:
            if any(j.status in ("running", "applying") for j in self.jobs.values()):
                raise BusyError("a sort is running; stop it first")
            self.jobs.clear()
        if include_cache:
            for model in ("clip", "siglip2"):
                self.cache_for(model).wipe()
            for d in (self.s.thumbs_dir, self.s.data_dir / "previews"):
                shutil.rmtree(d, ignore_errors=True)
                d.mkdir(parents=True, exist_ok=True)

    def mark_undone(self, run_id: str) -> None:
        """After Undo the files are back: the sort is a plan again (can be edited and applied)."""
        job = next((j for j in self.jobs.values() if j.run_id == run_id), None)
        if job is None and getattr(self, "db", None):
            d = self.db.job_for_run(run_id)
            job = self.get(d["id"]) if d else None
        if job and job.status == "applied":
            job.status, job.run_id = "done", None
            self._persist(job)

    def cancel(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job or job.finished:
            return False
        job.cancel_requested = True
        return True

    def apply(self, job_id: str, mode: str) -> dict:
        job = self.get(job_id)
        if not job:
            raise KeyError(job_id)
        with self._lock:
            if job.status != "done":
                raise BusyError(f"job is {job.status}; only a finished, unapplied job can be applied")
            job.status = "applying"
        try:
            journal = apply_plan(
                self.s.library_root,
                [{"rel_path": p["rel_path"], "destination": p["destination"], "sidecars": p.get("sidecars") or [],
                  "xmp": p.get("xmp"), "also": p.get("also") or []} for p in job.plan],
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
        self._persist(job)
        return journal

    def _xmp_for(self, fid, cid, quality, rules, bursts) -> dict | None:
        """Lightroom/Capture One rating & label: rejects -1/Red, picks 5/Green, else stars from the keeper score."""
        q = quality.get(fid)
        if q is None:
            return None
        rejected = cid in REASONS or cid.startswith("_reject-") or (bursts.get(fid) and not bursts[fid]["best"])
        if rejected:
            return {"rating": -1, "label": "Red"}
        recommended = getattr(self, "_pick_info", {}).get(fid)
        rating = stars(recommended["score"] if recommended else score(q, rules))
        return {"rating": rating, "label": "Green" if cid == "picks" else None}

    def reassign(self, job_id: str, file_ids: list[str], category_id: str) -> dict:
        """Manual override before Apply: move files to another category of the same job."""
        job = self.get(job_id)
        if not job:
            raise KeyError(job_id)
        if job.status != "done":
            raise BusyError(f"job is {job.status}; plans can only be edited before Apply")
        cats = {c["id"]: c for c in job.categories}
        extra = {UNSORTED["id"]: UNSORTED, DUPLICATES["id"]: DUPLICATES}
        cat = cats.get(category_id) or extra.get(category_id)
        if not cat:
            raise ValueError("unknown category")
        if cat.get("media") in ("image", "video"):
            kinds = {p["file_id"]: p["kind"] for p in job.plan}
            if any(kinds.get(fid) not in (None, cat["media"]) for fid in file_ids):
                raise ValueError(f"{cat['name']} only accepts {cat['media']}s")
        wanted = set(file_ids)
        opts = job.request.get("options", {})
        out_dir = opts.get("output_dir")
        out_dir = self.s.output_dir_name if out_dir is None else out_dir.strip()
        source = job.request.get("source") or ""
        source_rel = source.strip("/")
        changed = []
        for p in job.plan:
            if p["file_id"] in wanted:
                p.update(category_id=cat["id"], category=cat["name"], source="manual", confidence=1.0,
                         destination=destination(source_rel, out_dir, p["kind"], cat, opts.get("split_media", True)))
                if p.get("pick"):
                    p["pick"]["picked"] = cat["id"] == "picks"
                if p.get("xmp"):
                    rejected = cat["id"] in REASONS or cat["id"].startswith("_reject-")
                    p["xmp"] = {"rating": -1 if rejected else (p.get("quality") or {}).get("stars", 1),
                                "label": "Red" if rejected else "Green" if cat["id"] == "picks" else None}
                changed.append(p)
        # recount
        counts: dict[str, dict[str, int]] = {}
        for p in job.plan:
            c = counts.setdefault(p["category_id"], {"photos": 0, "videos": 0})
            c["photos" if p["kind"] == "image" else "videos"] += 1
        if cat["id"] not in cats:
            job.categories.append(dict(cat))
        job.categories = [{**c, **counts.get(c["id"], {"photos": 0, "videos": 0})} for c in job.categories]
        job.stats["folders"] = len({p["destination"] for p in job.plan if p["category_id"] != DUPLICATES["id"]})
        self._persist(job)
        return {"changed": changed, "categories": job.categories, "stats": job.stats}

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
            self._record_stats(job)
            self._persist(job)

    def _record_stats(self, job: Job) -> None:
        """Per-sort statistics (Statistics tab): wall time, time per phase, counts, model, AI usage."""
        if not getattr(self, "db", None):
            return
        phases: dict[str, float] = {}
        marks = job.phase_times + [("_end", job.finished_at or time.time())]
        for (name, t0), (_, t1) in zip(marks, marks[1:]):
            phases[name] = round(phases.get(name, 0.0) + (t1 - t0), 3)
        st = job.stats or {}
        opts = job.request.get("options", {})
        try:
            self.db.add_job_stats(job.id, {
                "job_id": job.id, "finished_at": job.finished_at, "status": job.status if job.status != "applying" else "done",
                "strategy": job.request.get("strategy"), "model": opts.get("model", "clip"),
                "source": job.request.get("source") or "", "files": st.get("total", 0), "photos": st.get("photos", 0),
                "videos": st.get("videos", 0), "embedded": st.get("embedded", 0), "duplicates": st.get("duplicates", 0),
                "folders": st.get("folders", 0), "wall": round((job.finished_at or time.time()) - job.created_at, 3),
                "phases": phases, "usage": job.usage,
            })
        except Exception as exc:  # noqa: BLE001 - statistics must never break a sort
            log.warning("could not record stats: %s", exc)

    def _phase(self, job: Job, phase: str) -> None:
        job.phase_times.append((phase, time.time()))
        job.phase = phase
        job.emit("phase", phase=phase)

    def _analyze_one(self, f: MediaFile, cache: AnalysisCache | None = None):
        key = str(f.path)
        cache = cache or self.cache
        try:
            cached = cache.get(key, f.size, f.mtime)
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

        # Compile before scanning: invalid AI destinations never produce a plan.
        if req["strategy"] == "rules":
            self._phase(job, "rules")
            llm = self._llm(job)
            if llm is None:
                raise ValueError("Prompt rules require AI; configure OPENAI_API_KEY")
            before = dict(llm.usage)
            try:
                opts["_rules"] = [r.to_dict() for r in llm.compile_rules(opts.get("rules_prompt", ""))]
            finally:
                job.usage = {k: llm.usage[k] - before[k] for k in before}
                job.usage["model"] = llm.model
            if job.cancel_requested:
                return

        # 1. scan
        self._phase(job, "scanning")
        out_dir = opts.get("output_dir")
        out_dir = self.s.output_dir_name if out_dir is None else out_dir.strip()
        files = scan(root, source, out_dir, recursive=opts.get("recursive", True),
                     pair_sidecars=opts.get("pair_sidecars", True))
        n_img = sum(f.kind == "image" for f in files)
        job.stats = {"total": len(files), "photos": n_img, "videos": len(files) - n_img,
                     "analyzed": 0, "folders": 0, "duplicates": 0, "errors": 0, "embedded": 0}
        job.emit("scanned", total=len(files), photos=n_img, videos=len(files) - n_img,
                 source=source_rel, source_name=source.name if source_rel else "Library")

        # 2. analyze: photos first (they are the main subject), videos after
        files.sort(key=lambda f: (f.kind != "image", f.rel_path))
        self._phase(job, "analyzing")
        model = opts.get("model", "clip")
        cache = self.cache_for(model)
        embedder = self.embedder_for(model) if files else None
        results: dict[str, tuple[MediaFile, Analysis, np.ndarray]] = {}
        with ThreadPoolExecutor(max_workers=self.s.workers) as ex:
            for start in range(0, len(files), CHUNK):
                if job.cancel_requested:
                    return
                chunk = files[start : start + CHUNK]
                pending: list[tuple[MediaFile, Any]] = []
                for kind, f, payload, emb in ex.map(lambda x: self._analyze_one(x, cache), chunk):
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
                        cache.put(str(f.path), f.size, f.mtime, d.analysis, emb)
                        results[f.id] = (f, d.analysis, emb)
                    job.stats["embedded"] += len(pending)
                job.stats["analyzed"] = len(results) + job.stats["errors"]
                job.emit("progress", analyzed=job.stats["analyzed"], total=len(files))

        ordered = [results[f.id] for f in files if f.id in results]

        # 2b. quality signals (culling): only when asked for
        qopts = opts.get("quality") or {}
        rules = QualityRules(**{k: qopts[k] for k in QualityRules.__dataclass_fields__ if k in qopts})
        need_quality = req["strategy"] == "cull" or qopts.get("enabled", False)
        quality: dict[str, Quality] = self._quality(job, ordered) if need_quality else {}
        if job.cancel_requested:
            return
        texts: dict[str, dict] = self._ocr(job, ordered) if opts.get("ocr") else {}
        faces: dict[str, list[FaceID]] = self._faces(job, ordered) if req["strategy"] == "people" else {}
        if job.cancel_requested:
            return
        # best-of-burst: near-identical shots seconds apart -> keep the best, mark the rest as extras
        bursts: dict[str, dict] = {}
        if need_quality and qopts.get("bursts", True):
            cand = [(f.id, str(Path(f.rel_path).parent), a.captured_at, e) for f, a, e in ordered
                    if f.kind == "image" and f.id in quality]
            window = 1e12 if qopts.get("similar_any_time") else float(qopts.get("burst_seconds", 2.0))
            groups = find_bursts(cand, window, float(qopts.get("burst_similarity", 0.9)))
            members: dict[int, list[str]] = {}
            for fid, g in groups.items():
                members.setdefault(g, []).append(fid)
            for g, ids in members.items():
                best = max(ids, key=lambda i: (verdict(quality[i], rules)[0] is None, score(quality[i], rules)))
                for i in ids:
                    bursts[i] = {"group": g, "size": len(ids), "best": i == best}
            job.stats["bursts"] = len(members)

        # 3. duplicates
        self._phase(job, "deduplicating")
        dup_items = [
            DupItem(f.id, f.kind, a.sha256, a.phash, (a.width or 0) * (a.height or 0), f.size, a.captured_at,
                    f.rel_path, a.duration, e)
            for f, a, e in ordered
        ]
        dup_map = find_duplicates(dup_items, near=opts.get("near_duplicates", True),
                                  max_distance=int(opts.get("near_dup_distance", 4)),
                                  keep=opts.get("duplicate_keep", "best"))
        job.stats["duplicates"] = len(dup_map)
        job.emit("stats", **job.stats)

        # 4. categorize
        self._phase(job, "categorizing")
        keep = [(f, a, e) for f, a, e in ordered if f.id not in dup_map]
        assignment, categories = self._categorize(job, keep, embedder, quality, rules, bursts, faces)
        if texts and req["strategy"] in ("preset", "custom"):
            self._text_override(job, keep, assignment, categories, texts, embedder, opts)
        if job.cancel_requested:
            return
        # reject overlay: bad shots leave their category for _Rejects/<reason>
        if need_quality and req["strategy"] != "cull" and qopts.get("action", "reject") == "reject":
            used: set[str] = set()
            for f, _, _ in keep:
                q = quality.get(f.id)
                reason = verdict(q, rules)[0] if q else None
                if not reason and f.id in bursts and not bursts[f.id]["best"]:
                    reason = "burst"
                if reason:
                    assignment[f.id] = (f"_reject-{reason}", 1.0, "quality")
                    used.add(reason)
            for reason in REASONS:
                if reason in used:
                    name, emoji = REASONS[reason]
                    categories.append({"id": f"_reject-{reason}", "name": f"Rejects · {name}", "emoji": emoji,
                                       "path": f"_Rejects/{name}"})

        # 5. plan
        if req["strategy"] != "people":
            self._extra = {}
        cats_by_id = {c["id"]: c for c in categories}
        if any(cid is None for cid, _, _ in assignment.values()):
            cats_by_id[UNSORTED["id"]] = dict(UNSORTED)
        dup_action = opts.get("duplicates_action", "folder")
        if dup_map:
            label = {"keep": "Duplicates (left in place)", "delete": "Duplicates → trash"}.get(dup_action, "Duplicates")
            cats_by_id[DUPLICATES["id"]] = {**DUPLICATES, "name": label}
        split = opts.get("split_media", True)
        trash_dir = "/".join(p for p in (source_rel, TRASH_DIR) if p)
        # keepers first, so duplicates can follow their original
        dest_of: dict[str, tuple[str, str]] = {}
        for f, a, e in ordered:
            if f.id not in dup_map:
                cid = assignment[f.id][0] or UNSORTED["id"]
                dest_of[f.id] = (cid, destination(source_rel, out_dir, f.kind, cats_by_id[cid], split))
        plan = []
        for f, a, e in ordered:
            if f.id in dup_map and dup_action == "with_original":
                cid, dest = dest_of[dup_map[f.id]]
                conf, src = 1.0, "duplicate"
            elif f.id in dup_map:
                cid, conf, src = DUPLICATES["id"], 1.0, "duplicate"
                parent = Path(f.rel_path).parent.as_posix()
                if dup_action == "keep":
                    dest = "" if parent == "." else parent  # same folder: apply skips it
                elif dup_action == "delete":
                    dest = trash_dir
                else:
                    dest = destination(source_rel, out_dir, f.kind, cats_by_id[cid], split)
            else:
                cid, conf, src = assignment[f.id]
                cid = cid or UNSORTED["id"]
                dest = dest_of[f.id][1]
                if cats_by_id[cid].get("stay"):  # left where it is: apply skips files already in place
                    parent = Path(f.rel_path).parent.as_posix()
                    dest = "" if parent == "." else parent
            cat = cats_by_id[cid]
            plan.append({
                "file_id": f.id, "rel_path": f.rel_path, "name": f.name, "kind": f.kind,
                "thumb": f"/api/thumbs/{a.sha256}", "category_id": cid, "category": cat["name"],
                "confidence": round(float(conf), 4), "source": src,
                "destination": dest,
                "duplicate_of": dup_map.get(f.id),
                "sidecars": list(f.sidecars),
                "quality": summary(quality[f.id], rules) if f.id in quality else None,
                "burst": bursts.get(f.id),
                "pick": getattr(self, "_pick_info", {}).get(f.id),
                "text": (texts.get(f.id) or {}).get("text") or None,
                "also": [destination(source_rel, out_dir, f.kind, cats_by_id[c], split) for c in sorted(getattr(self, "_extra", {}).get(f.id, ()))
                         if c in cats_by_id] or None,
                "xmp": self._xmp_for(f.id, cid, quality, rules, bursts) if qopts.get("write_xmp") and f.kind == "image" else None,
            })
        for item in plan:
            if item.get("quality") and item.get("pick"):
                item["quality"]["score"] = item["pick"]["score"]
                item["quality"]["stars"] = stars(item["pick"]["score"])
        counts: dict[str, dict[str, int]] = {}
        for p in plan:
            c = counts.setdefault(p["category_id"], {"photos": 0, "videos": 0})
            c["photos" if p["kind"] == "image" else "videos"] += 1
        order = list(dict.fromkeys([c["id"] for c in categories] + [UNSORTED["id"], DUPLICATES["id"]]))
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
    def _quality(self, job: Job, ordered) -> dict[str, Quality]:
        """Compute (or load cached) quality signals for photos. Videos are skipped."""
        self._phase(job, "checking")
        fa = get_face_analyzer()
        if not fa.available:
            job.warnings.append("Face model not available: eyes/smile checks skipped")
            job.emit("warning", message=job.warnings[-1])
        photos = [f for f, _, _ in ordered if f.kind == "image"]
        out: dict[str, Quality] = {}

        def one(f: MediaFile):
            if job.cancel_requested:
                return f, None
            cached = self.cache.get_quality(str(f.path), f.size, f.mtime)
            if cached and cached.get("v", 1) >= QUALITY_VERSION and (cached.get("faces_checked") or not fa.available):
                return f, Quality.from_dict(cached)
            try:
                q = analyze_image(load_for_quality(f.path), fa)
            except Exception as exc:  # noqa: BLE001
                log.warning("quality check failed for %s: %s", f.rel_path, exc)
                return f, None
            self.cache.put_quality(str(f.path), f.size, f.mtime, q.to_dict())
            return f, q

        with ThreadPoolExecutor(max_workers=self.s.workers) as ex:
            for n, (f, q) in enumerate(ex.map(one, photos), 1):
                if q is not None:
                    out[f.id] = q
                if n % 8 == 0 or n == len(photos):
                    job.emit("progress", analyzed=n, total=len(photos), stage="quality")
        unchecked = sum(1 for q in out.values() if not q.faces_checked)
        if fa.available and unchecked:
            job.warnings.append(f"Face detection failed on {unchecked} photos: eyes/smile checks skipped for them")
            job.emit("warning", message=job.warnings[-1])
        return out

    # ------------------------------------------------------------ OCR
    def _ocr(self, job: Job, ordered) -> dict[str, dict]:
        reader = get_text_reader()
        if not reader.available:
            job.warnings.append("OCR is not available in this build")
            return {}
        self._phase(job, "reading")
        photos = [f for f, _, _ in ordered if f.kind == "image"]

        def one(f: MediaFile):
            cached = self.cache.get_json("ocr", str(f.path), f.size, f.mtime)
            if cached is not None:
                return f, cached
            try:
                r = reader.read(load_for_quality(f.path, 1024))
            except Exception as exc:  # noqa: BLE001
                log.warning("ocr failed for %s: %s", f.rel_path, exc)
                return f, None
            self.cache.put_json("ocr", str(f.path), f.size, f.mtime, r)
            return f, r

        out = {}
        with ThreadPoolExecutor(max_workers=max(1, self.s.workers // 2)) as ex:
            for n, (f, r) in enumerate(ex.map(one, photos), 1):
                if r:
                    out[f.id] = r
                if n % 8 == 0 or n == len(photos):
                    job.emit("progress", analyzed=n, total=len(photos), stage="ocr")
        return out

    def _text_override(self, job, keep, assignment, cats, texts, embedder, opts) -> None:
        """Photos that are mostly text go to the set's text-like folder (documents, captions, screenshots…)."""
        targets = text_category(cats)
        if not targets:
            return
        min_chars, min_cov = int(opts.get("ocr_min_chars", 25)), float(opts.get("ocr_min_coverage", 0.03))
        tm = classify.category_matrix(embedder, targets)
        target_ids = {c["id"] for c in targets}
        for f, _, e in keep:
            t = texts.get(f.id)
            if not t or t["chars"] < min_chars or t["coverage"] < min_cov or assignment[f.id][0] in target_ids:
                continue
            best = targets[int(np.argmax(tm @ e))]
            assignment[f.id] = (best["id"], assignment[f.id][1], "ocr")

    # ------------------------------------------------------------ people
    def _faces(self, job: Job, ordered) -> dict[str, list[FaceID]]:
        ident = get_face_identifier()
        if not ident.available:
            job.warnings.append("Face identity models are missing: everything goes to 'No people'")
            return {}
        self._phase(job, "faces")
        photos = [f for f, _, _ in ordered if f.kind == "image"]

        def one(f: MediaFile):
            cached = self.cache.get_json("faceid", str(f.path), f.size, f.mtime)
            if cached is not None:
                return f, [FaceID.from_dict(d) for d in cached]
            try:
                found = ident.identify(load_for_quality(f.path, 1600))
            except Exception as exc:  # noqa: BLE001
                log.warning("face id failed for %s: %s", f.rel_path, exc)
                return f, []
            self.cache.put_json("faceid", str(f.path), f.size, f.mtime, [x.to_dict() for x in found])
            return f, found

        out = {}
        with ThreadPoolExecutor(max_workers=self.s.workers) as ex:
            for n, (f, found) in enumerate(ex.map(one, photos), 1):
                out[f.id] = found
                if n % 8 == 0 or n == len(photos):
                    job.emit("progress", analyzed=n, total=len(photos), stage="faces")
        return out

    def _faceless(self, keep, assignment, people, main, group_ids, embedder, multi) -> None:
        bank = text_bank(embedder)
        ids = [f.id for f, _, _ in keep]
        E = np.vstack([e / (np.linalg.norm(e) + 1e-9) for _, _, e in keep]).astype(np.float32)
        row = {fid: i for i, fid in enumerate(ids)}
        # remove what the whole shoot shares (B&W, location, light): what's left is mostly the person
        C = E - E.mean(axis=0, keepdims=True)
        C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-9
        pman = man_probability(E, bank)
        by_id = {f.id: f for f, _, _ in keep}
        protos, proto_man = [], []
        for m in people:
            v = C[[row[i] for i in m]].mean(axis=0)
            protos.append(v / (np.linalg.norm(v) + 1e-9))
            proto_man.append(self._face_gender(m, main, by_id, embedder, bank, fallback=float(np.mean([pman[row[i]] for i in m]))))
        cand = [f for f, _, _ in keep if f.kind == "image" and f.id not in assignment and f.id not in main and f.id not in group_ids]
        if not cand:
            return
        idx = [row[f.id] for f in cand]
        present = person_presence(E[idx], bank)
        res = assign_by_appearance(C[idx], np.vstack(protos), np.asarray(proto_man), pman[idx], present=present)
        log.info("appearance: people gender=%s, candidates=%d, present=%d, matched=%d", [round(x, 2) for x in proto_man],
                 len(cand), int((present >= 0.45).sum()), sum(1 for r in res if r[0] >= 0))
        for f, p, (best, sc, close) in zip(cand, present, res):
            if p < 0.45 or best < 0:
                continue
            assignment[f.id] = (f"person-{best + 1}", round(float(min(1.0, max(0.0, 0.5 + sc))), 4), "appearance")
            if multi == "copy":
                for j in close:
                    if j != best:
                        self._extra.setdefault(f.id, set()).add(f"person-{j + 1}")

    def _face_gender(self, members, main, by_id, embedder, bank, fallback: float, n: int = 5) -> float:
        """How much a person reads as a man, judged on crops of their own face (their photos often show others too)."""
        crops = []
        for fid in sorted(members, key=lambda i: -main[i].area if i in main else 0)[:n]:
            if fid not in main:
                continue
            try:
                img = load_for_quality(by_id[fid].path, 1200)
                w, h = img.size
                x0, y0, x1, y1 = main[fid].box
                cx, cy, bw, bh = (x0 + x1) / 2 * w, (y0 + y1) / 2 * h, (x1 - x0) * w, (y1 - y0) * h
                side = max(bw, bh) * 2.2  # head and shoulders
                box = (max(0, cx - side / 2), max(0, cy - side / 2), min(w, cx + side / 2), min(h, cy + side * 0.7))
                crops.append(img.crop(tuple(int(v) for v in box)).convert("RGB"))
            except Exception as exc:  # noqa: BLE001
                log.debug("face crop failed: %s", exc)
        if not crops:
            return fallback
        X = np.asarray(embedder.embed_images(crops), dtype=np.float32)
        X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
        return float(np.median(man_probability(X, bank)))

    def reference_face(self, data: bytes) -> dict:
        """Reference photo → the largest face's identity embedding and an avatar. Raises ValueError if no face."""
        import io

        ident = get_face_identifier()
        if ident is None:
            raise ValueError("face recognition is not available")
        try:
            with Image.open(io.BytesIO(data)) as im:
                img = ImageOps.exif_transpose(im).convert("RGB")
        except Exception as exc:  # noqa: BLE001
            raise ValueError("not a readable image") from exc
        img.thumbnail((1600, 1600))
        found = ident.identify(img)
        if not found:
            raise ValueError("no face found in this photo; use a clear, front-facing photo")
        face = max(found, key=lambda x: x.area)
        avatar = face_crop_webp(img, face.box)
        sha = hashlib.sha256(avatar).hexdigest()
        tp = self.thumb_path(sha)
        tp.parent.mkdir(parents=True, exist_ok=True)
        tp.write_bytes(avatar)
        return {"emb": [float(x) for x in face.emb], "cover": f"/api/thumbs/{sha}", "faces_in_photo": len(found)}

    def _people_ref(self, keep, faces, opts, ref) -> tuple[dict, list[dict]]:
        """Only photos showing the reference person move (into their folder); everything else stays where it is."""
        threshold = float(opts.get("people_similarity", 0.363))
        emb = np.asarray(ref["emb"], dtype=np.float32)
        emb /= np.linalg.norm(emb) or 1.0
        cid = "person-ref"
        assignment: dict[str, tuple[str | None, float, str]] = {}
        hits = 0
        for f, _, _ in keep:
            best = max((float(x.emb @ emb) for x in faces.get(f.id) or []), default=-1.0)
            if best >= threshold:
                assignment[f.id] = (cid, round(best, 4), "faces")
                hits += 1
            else:
                assignment[f.id] = ("others-stay", 1.0, "faces")
        cats = [{"id": cid, "name": ref.get("name") or "This person", "emoji": "🎯", "cover": ref.get("cover")}]
        cats.append({"id": "others-stay", "name": "Everything else (left in place)", "emoji": "📍", "stay": True})
        return assignment, cats

    def _people(self, job, keep, faces, opts, embedder=None) -> tuple[dict, list[dict]]:
        if opts.get("_people_ref"):
            self._extra = {}
            return self._people_ref(keep, faces, opts, opts["_people_ref"])
        """One folder per recurring person (by the photo's main face); Groups, Other people, No people, Videos."""
        multi = opts.get("people_multi", "main")  # "main" = only the biggest face decides; "copy" = every person gets a copy
        min_photos = int(opts.get("people_min_photos", 3))
        threshold = float(opts.get("people_similarity", 0.363))
        group_size = int(opts.get("people_group_size", 3))
        main: dict[str, FaceID] = {}
        group_ids: set[str] = set()
        for f, _, _ in keep:
            fs = faces.get(f.id) or []
            if not fs:
                continue
            biggest = max(fs, key=lambda x: x.area)
            sizable = [x for x in fs if x.area >= biggest.area * 0.4]
            if len(sizable) >= group_size:
                group_ids.add(f.id)
            else:
                main[f.id] = biggest
        ids = list(main)
        labels = cluster_people(np.vstack([main[i].emb for i in ids]) if ids else np.zeros((0, 128)), threshold)
        members: dict[int, list[str]] = {}
        for fid, lab in zip(ids, labels):
            members.setdefault(int(lab), []).append(fid)
        people = sorted((m for m in members.values() if len(m) >= min_photos), key=len, reverse=True)
        cats: list[dict] = []
        assignment: dict[str, tuple[str | None, float, str]] = {}
        self._extra: dict[str, set] = {}
        by_id = {f.id: f for f, _, _ in keep}
        for n, m in enumerate(people, 1):
            cid = f"person-{n}"
            best = max(m, key=lambda i: main[i].area)
            cover = None
            try:
                img = load_for_quality(by_id[best].path, 1600)
                data = face_crop_webp(img, main[best].box)
                sha = hashlib.sha256(data).hexdigest()
                tp = self.thumb_path(sha)
                tp.parent.mkdir(parents=True, exist_ok=True)
                tp.write_bytes(data)
                cover = f"/api/thumbs/{sha}"
            except Exception as exc:  # noqa: BLE001
                log.warning("avatar failed: %s", exc)
            cats.append({"id": cid, "name": f"Person {n}", "emoji": "🙂", "cover": cover})
            for fid in m:
                assignment[fid] = (cid, 1.0, "faces")
        if multi == "copy":
            # every other sizable face that matches a person → extra copy of the photo into that person's folder
            protos = {f"person-{n}": np.vstack([main[i].emb for i in m]).mean(axis=0) for n, m in enumerate(people, 1)}
            for f, _, _ in keep:
                fs = faces.get(f.id) or []
                if len(fs) < 2:
                    continue
                biggest = max(fs, key=lambda x: x.area)
                for x in fs:
                    if x is biggest or x.area < biggest.area * 0.25:
                        continue
                    best = max(protos.items(), key=lambda kv: float(x.emb @ (kv[1] / (np.linalg.norm(kv[1]) or 1))), default=None)
                    if best and float(x.emb @ (best[1] / (np.linalg.norm(best[1]) or 1))) >= threshold:
                        if assignment.get(f.id, (None,))[0] != best[0]:
                            self._extra.setdefault(f.id, set()).add(best[0])
        # people whose face can't be seen (back, far away, hands, veil…): match by appearance + man/woman cue
        if people and embedder is not None and opts.get("people_appearance", True):
            try:
                self._faceless(keep, assignment, people, main, group_ids, embedder, multi)
            except Exception as exc:  # noqa: BLE001 - never fail a sort over this
                log.warning("appearance matching skipped: %s", exc)
        extra = [("groups", "Groups", "👥"), ("other-people", "Other people", "🧑‍🤝‍🧑"), ("no-people", "No people", "🏞️"),
                 ("videos", "Videos", "🎬")]
        for f, _, _ in keep:
            if f.id in assignment:
                continue
            if f.kind == "video":
                assignment[f.id] = ("videos", 1.0, "faces")
            elif f.id in group_ids:
                assignment[f.id] = ("groups", 1.0, "faces")
            elif f.id in main:
                assignment[f.id] = ("other-people", 1.0, "faces")
            else:
                assignment[f.id] = ("no-people", 1.0, "faces")
        used = {a[0] for a in assignment.values()}
        cats += [{"id": i, "name": n, "emoji": e} for i, n, e in extra if i in used]
        return assignment, cats

    def rename_category(self, job_id: str, category_id: str, name: str) -> dict:
        """Rename a folder of a finished, unapplied job (e.g. Person 1 → Laura)."""
        job = self.get(job_id)
        if not job:
            raise KeyError(job_id)
        if job.status != "done":
            raise BusyError("only a finished, unapplied plan can be renamed")
        name = name.strip()
        if not name or len(name) > 60 or any(ch in name for ch in '/\\:*?"<>|'):
            raise ValueError("invalid folder name")
        if any(c["name"].lower() == name.lower() and c["id"] != category_id for c in job.categories):
            raise ValueError("another folder already has this name")
        cat = next((c for c in job.categories if c["id"] == category_id), None)
        if not cat:
            raise ValueError("unknown category")
        cat["name"] = name
        opts = job.request.get("options", {})
        out_dir = opts.get("output_dir")
        out_dir = self.s.output_dir_name if out_dir is None else out_dir.strip()
        source_rel = (job.request.get("source") or "").strip("/")
        for p in job.plan:
            if p["category_id"] == category_id:
                p["category"] = name
                p["destination"] = destination(source_rel, out_dir, p["kind"], cat, opts.get("split_media", True))
        self._persist(job)
        return {"categories": job.categories, "plan": [p for p in job.plan if p["category_id"] == category_id]}

    def _categorize(self, job: Job, keep, embedder, quality=None, rules=None, bursts=None, faces=None) -> tuple[dict, list[dict]]:
        req, opts = job.request, job.request.get("options", {})
        strategy = req["strategy"]
        self._pick_info: dict[str, dict] = {}
        assignment: dict[str, tuple[str | None, float, str]] = {}
        if not keep:
            return assignment, []
        embs = np.vstack([e for _, _, e in keep]) if keep else np.zeros((0, 512), np.float32)

        if strategy == "rules":
            return self._route_rules(job, keep)

        if strategy == "people":
            return self._people(job, keep, faces or {}, opts, embedder)

        if strategy == "cull":
            qopts = opts.get("quality") or {}
            smiles = qopts.get("smiles", True)
            min_stars = int(qopts.get("keeper_min_stars", 0))
            cats = [{"id": "keepers", "name": "Keepers", "emoji": "✅"}]
            if smiles:
                cats.append({"id": "smiling", "name": "Smiling", "emoji": "😄"})
            cats.append({"id": "maybe", "name": "Maybe", "emoji": "🤔"})
            for reason, (name, emoji) in REASONS.items():
                cats.append({"id": reason, "name": name, "emoji": emoji})
            cats.append({"id": "videos", "name": "Videos", "emoji": "🎬", "media": "video"})
            picks_pct = float(qopts.get("picks_percent", 0))
            if picks_pct > 0:
                cats.insert(0, {"id": "picks", "name": "Picks ★", "emoji": "🏆"})
            photos = [(f.id, e) for f, _, e in keep if f.kind == "image" and f.id in (quality or {})]
            ids = [fid for fid, _ in photos]
            E = np.vstack([e for _, e in photos]).astype(np.float32) if photos else np.empty((0, embs.shape[1]))
            ranking = picks_mod.rank(ids, quality or {}, E, embedder, rules, qopts.get("pick_profile", "auto"))
            self._pick_info = {fid: {"score": pi.score, "reasons": pi.reasons, "picked": False,
                                   "parts": pi.parts, "profile": pi.profile} for fid, pi in ranking.info.items()}
            # Choose the strongest expression/presentation within each burst, not merely its sharpest frame.
            for group in {b["group"] for b in (bursts or {}).values()}:
                members = [fid for fid in ids if (bursts or {}).get(fid, {}).get("group") == group]
                if members:
                    best = max(members, key=lambda fid: ranking.info[fid].score)
                    for fid in members:
                        bursts[fid]["best"] = fid == best
            used: set[str] = set()
            for f, _, _ in keep:
                if f.kind == "video":
                    cid = "videos"
                else:
                    q = (quality or {}).get(f.id)
                    reason, _, smiling = verdict(q, rules) if q else (None, [], False)
                    b = (bursts or {}).get(f.id)
                    if not reason and b and not b["best"]:
                        reason = "burst"
                    if reason:
                        cid = reason
                    elif min_stars and q and stars(ranking.info[f.id].score if f.id in ranking.info else score(q, rules)) < min_stars:
                        cid = "maybe"
                    else:
                        cid = "smiling" if smiles and smiling else "keepers"
                assignment[f.id] = (cid, 1.0, "quality")
                used.add(cid)
            if picks_pct > 0:
                kept = [(f.id, e) for f, _, e in keep if assignment[f.id][0] in ("keepers", "smiling") and f.id in (quality or {})]
                if kept:
                    ids = [k[0] for k in kept]
                    E = np.vstack([k[1] for k in kept]).astype(np.float32)
                    positions = {fid: i for i, fid in enumerate(ranking.info)}
                    subset = picks_mod.Ranking(ranking.info, np.array([ranking.labels[positions[fid]] for fid in ids]))
                    n_picks = max(1, round(len(ids) * picks_pct / 100))
                    chosen = set(picks_mod.select(ids, subset, E, n_picks))
                    for fid in chosen:
                        self._pick_info[fid]["picked"] = True
                    for fid in chosen:
                        assignment[fid] = ("picks", ranking.info[fid].score, "quality")
                        used.add("picks")
            return assignment, [c for c in cats if c["id"] in used]

        if strategy in ("trips", "places"):
            self._phase(job, "locating")
            files = [f for f, _, _ in keep]
            geo = locate_files(self.cache, files)
            add_places(geo)
            if strategy == "places":
                by_city = opts.get("place_granularity", "country") == "city"
                names: dict[str, str] = {}
                for f in files:
                    pl = (geo.get(f.id) or {}).get("place")
                    if not pl or not pl.get("country"):
                        names[f.id] = "No location"
                    elif by_city and pl.get("city"):
                        names[f.id] = f"{pl['city']}, {pl['country']}"
                    else:
                        names[f.id] = pl["country"]
                uniq = sorted(set(names.values()) - {"No location"}) + (["No location"] if "No location" in names.values() else [])
                cats = [{"id": "p-" + slugify(n), "name": n, "emoji": "📍" if n != "No location" else "❔"} for n in uniq]
                ids = {c["name"]: c["id"] for c in cats}
                for f in files:
                    assignment[f.id] = (ids[names[f.id]], 1.0, "gps")
                return assignment, cats
            trips, _home = trips_for(files, geo, captured={f.id: a.captured_at for f, a, _ in keep},
                                     away_km=float(opts.get("trip_away_km", 80)), gap_hours=float(opts.get("trip_gap_hours", 36)),
                                     min_photos=int(opts.get("trip_min_photos", 5)))
            cats = []
            for n, t in enumerate(sorted(trips, key=lambda t: t.start), 1):
                cid = f"trip-{n}"
                cats.append({"id": cid, "name": t.name(), "emoji": "✈️"})
                for i in t.ids:
                    assignment[i] = (cid, 1.0, "gps")
            rest = [f for f in files if f.id not in assignment]
            if rest:
                cats.append({"id": "everyday", "name": "Everyday", "emoji": "🏠"})
                for f in rest:
                    assignment[f.id] = ("everyday", 1.0, "gps")
            return assignment, cats

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
            focus = opts.get("focus", "auto")
            gran = opts.get("granularity", "normal")
            max_k = int(opts.get("max_clusters", 12))
            max_k, bias = {"coarse": (min(max_k, 6), -0.002), "fine": (max_k + 6, 0.01)}.get(gran, (max_k, 0.003))
            # 1) what is this collection? (context for naming, shown in the UI)
            theme, theme_conf = classify.collection_theme(embs, embedder)
            job.context = {"theme": theme, "confidence": round(theme_conf, 3), "focus": focus}
            job.emit("context", **job.context)
            # 2) cluster on raw CLIP (auto) or on z-scored facet features (scene / framing / outfit / lighting …)
            bank_labels, bank, facet_of = classify.facet_bank(embedder, FOCUS_FACETS.get(focus, FOCUS_FACETS["auto"]))
            z = classify.facet_features(embs, bank)
            X = embs if focus == "auto" else normalize(z)
            labels, cents = classify.choose_k(X, max_k, bias=bias)
            # 3) local names = what makes each group stand out within this folder
            local = classify.unique_names(classify.describe_clusters(z, labels, len(cents), bank_labels, facet_of))
            names = self._name_clusters(job, keep, X, labels, cents, local, theme, focus)
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
            for i, (f, _, _) in enumerate(keep):
                ci = int(labels[i])
                assignment[f.id] = (label_to_cat[ci], float(max(0.0, X[i] @ cents[ci])), "cluster")
            return assignment, cats

        # preset / custom
        cset = self.store.get(req.get("set_id") or "")
        if not cset:
            raise KeyError("category set not found")
        cats = [dict(c) for c in cset["categories"]]
        res = classify.classify_with_set(
            embs, [a.is_screenshot for _, a, _ in keep], cats, embedder, float(opts.get("min_confidence", 0.3)),
            kinds=[f.kind for f, _, _ in keep],
        )
        for (f, _, _), r in zip(keep, res):
            assignment[f.id] = r
        if opts.get("ai_assist"):
            scope = ((opts.get("ai") or {}).get("assist_scope")) or "unsure"
            self._assist(job, keep, assignment, cats, int(opts.get("ai_max_files", 200)), scope)
        return assignment, cats

    def _route_rules(self, job: Job, keep) -> tuple[dict, list[dict]]:
        rules = validate_rules(job.request["options"]["_rules"])
        cats = [{"id": f"rule-{i}", "name": r.folder, "path": r.folder, "emoji": "📁"} for i, r in enumerate(rules)]
        llm = self._llm(job)
        if llm is None:
            raise ValueError("AI became unavailable while matching prompt rules")
        self._phase(job, "ai")
        assignment = {}
        # Bounded batches allow cancellation between calls and avoid retaining the whole library as PIL images.
        size = max(1, min(24, int(llm.assist_batch))) * 6
        before = dict(llm.usage)
        try:
            for start in range(0, len(keep), size):
                if job.cancel_requested:
                    return {}, cats
                chunk = keep[start:start + size]
                thumbs = [load_thumb(self.thumb_path(a.sha256)) for _, a, _ in chunk]
                if any(t is None for t in thumbs):
                    raise ValueError("A thumbnail is unavailable; run the sort again")
                labels = llm.classify_rules(thumbs, rules)
                for (f, _, _), index in zip(chunk, labels):
                    assignment[f.id] = (None if index is None else cats[index]["id"], 1.0, "ai")
        finally:
            previous = job.usage or {}
            job.usage = {key: previous.get(key, 0) + llm.usage[key] - before[key] for key in before}
            job.usage["model"] = llm.model
        return assignment, cats

    def _llm(self, job: Job) -> LLMClient | None:
        try:
            llm = self.llm_factory()
            ai = (job.request.get("options") or {}).get("ai") or {}
            if llm is not None:
                if ai.get("model"):
                    llm.model = ai["model"]
                if ai.get("reasoning_effort"):
                    llm.effort = ai["reasoning_effort"]
                llm.naming_prompt = ai.get("naming_prompt") or ""
                llm.assist_prompt = ai.get("assist_prompt") or ""
                llm.naming_instructions = ai.get("naming_instructions") or ""
                llm.assist_instructions = ai.get("assist_instructions") or ""
                llm.assist_batch = int(ai.get("assist_batch") or llm.assist_batch)
            return llm
        except Exception as exc:  # noqa: BLE001
            job.warnings.append(f"AI unavailable: {exc}")
            return None

    def _name_clusters(self, job, keep, X, labels, cents, local, theme, focus) -> list[tuple[str, str]]:
        fallback = [(n, "📁") for n in local]
        llm = self._llm(job)
        if not llm:
            return fallback
        try:
            reps = classify.representatives(X, labels, cents)
            sheets = [contact_sheet([self.thumb_path(keep[i][1].sha256) for i in r]) for r in reps]
            rng = random.Random(job.id)
            sample = rng.sample(range(len(keep)), min(12, len(keep)))
            overview = contact_sheet([self.thumb_path(keep[i][1].sha256) for i in sample], cols=4, rows=3, cell=96)
            collection, ai = llm.name_clusters(sheets, overview=overview, theme_hint=theme, focus_hint=FOCUS_HINT.get(focus, ""),
                                               local_hints=local)
            job.usage = dict(llm.usage, model=llm.model)
            if collection:
                job.context = {**(job.context or {}), "theme": collection, "source": "ai"}
                job.emit("context", **job.context)
            return [(n, e) if n else fallback[i] for i, (n, e) in enumerate(ai)]
        except Exception as exc:  # noqa: BLE001 - REQ-CAT-9 graceful fallback
            log.warning("cluster naming failed: %s", exc)
            job.warnings.append(f"AI naming failed, used local names ({type(exc).__name__})")
            job.emit("warning", message=job.warnings[-1])
            return fallback

    def _assist(self, job, keep, assignment, cats, max_files: int, scope: str = "unsure") -> None:
        """AI picks the folder: for uncertain files only (cheap) or for every file (most accurate)."""
        if scope == "all":
            unsure = [(f, a) for f, a, _ in keep][:max_files]
        else:
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
            folders = [{"name": c["name"], "hint": c.get("ai_hint") or "; ".join((c.get("prompts") or [])[:2])
                        + (" (videos only)" if c.get("media") == "video" else "")} for c in cats]
            job.emit("phase", phase="ai")
            labels = llm.assist(thumbs, folders)
        except Exception as exc:  # noqa: BLE001
            log.warning("assist failed: %s", exc)
            job.warnings.append(f"AI assist failed, kept local results ({type(exc).__name__})")
            job.emit("warning", message=job.warnings[-1])
            return
        finally:
            job.usage = dict(llm.usage, model=llm.model)
        name_to_cat = {c["name"].lower(): c for c in cats}
        for f, label in zip(owners, labels):
            cat = name_to_cat.get(label.lower())
            cid = cat["id"] if cat and (cat.get("media") or "any") in ("any", f.kind) else None
            if cid:
                assignment[f.id] = (cid, assignment[f.id][1], "ai")
