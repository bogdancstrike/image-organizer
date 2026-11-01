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
from .media import Analysis, MediaError, decode, load_for_quality
from .quality import REASONS, Quality, QualityRules, analyze_image, find_bursts, get_face_analyzer, score, stars, summary, verdict
from .organizer import apply_plan
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
                [{"rel_path": p["rel_path"], "destination": p["destination"], "sidecars": p.get("sidecars") or [],
                  "xmp": p.get("xmp")} for p in job.plan],
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

    @staticmethod
    def _xmp_for(fid, cid, quality, rules, bursts) -> dict | None:
        """Lightroom/Capture One rating & label: rejects -1/Red, picks 5/Green, else stars from the keeper score."""
        q = quality.get(fid)
        if q is None:
            return None
        rejected = cid in REASONS or cid.startswith("_reject-") or (bursts.get(fid) and not bursts[fid]["best"])
        if rejected:
            return {"rating": -1, "label": "Red"}
        if cid == "picks":
            return {"rating": 5, "label": "Green"}
        return {"rating": stars(score(q, rules)), "label": None}

    def reassign(self, job_id: str, file_ids: list[str], category_id: str) -> dict:
        """Manual override before Apply: move files to another category of the same job."""
        job = self.jobs.get(job_id)
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

        # 2b. quality signals (culling): only when asked for
        qopts = opts.get("quality") or {}
        rules = QualityRules(**{k: qopts[k] for k in QualityRules.__dataclass_fields__ if k in qopts})
        need_quality = req["strategy"] == "cull" or qopts.get("enabled", False)
        quality: dict[str, Quality] = self._quality(job, ordered) if need_quality else {}
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
        assignment, categories = self._categorize(job, keep, embedder, quality, rules, bursts)
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
                "xmp": self._xmp_for(f.id, cid, quality, rules, bursts) if qopts.get("write_xmp") and f.kind == "image" else None,
            })
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
            if cached and "noise" in cached and (cached.get("faces_checked") or not fa.available):
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

    def _categorize(self, job: Job, keep, embedder, quality=None, rules=None, bursts=None) -> tuple[dict, list[dict]]:
        req, opts = job.request, job.request.get("options", {})
        strategy = req["strategy"]
        assignment: dict[str, tuple[str | None, float, str]] = {}
        if not keep:
            return assignment, []
        embs = np.vstack([e for _, _, e in keep]) if keep else np.zeros((0, 512), np.float32)

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
                    elif min_stars and q and stars(score(q, rules)) < min_stars:
                        cid = "maybe"
                    else:
                        cid = "smiling" if smiles and smiling else "keepers"
                assignment[f.id] = (cid, 1.0, "quality")
                used.add(cid)
            if picks_pct > 0:
                kept = [f.id for f, _, _ in keep if assignment[f.id][0] in ("keepers", "smiling") and f.id in (quality or {})]
                n_picks = max(1, round(len(kept) * picks_pct / 100)) if kept else 0
                for fid in sorted(kept, key=lambda i: -score(quality[i], rules))[:n_picks]:
                    assignment[fid] = ("picks", 1.0, "quality")
                    used.add("picks")
            return assignment, [c for c in cats if c["id"] in used]

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
