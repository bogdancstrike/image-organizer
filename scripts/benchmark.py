#!/usr/bin/env python3
"""Benchmark a running Auto Image Organizer through its API (plans only, nothing is moved).

Usage:
  python3 scripts/benchmark.py --source "path/under/LIBRARY_PATH" [--strategy preset --set lifestyle] [--runs 2]
  python3 scripts/benchmark.py --suite suite.json      # [{"label": "...", "body": {...JobRequest...}}, ...]

Prints a Markdown table: files, wall time, files/s, and phase timings taken from the event stream.
Run once on an empty cache (cold: delete data/cache.db and data/thumbs while the app is stopped) and again (warm).
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request

BASE = "http://localhost:8080"


def call(method: str, path: str, body=None):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode() if body is not None else None, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def run(body: dict) -> dict:
    t0 = time.perf_counter()
    job_id = call("POST", "/api/jobs", body)["id"]
    phases: dict[str, float] = {}
    last_phase, last_t = None, t0
    # follow the SSE stream for phase timings
    with urllib.request.urlopen(f"{BASE}/api/jobs/{job_id}/events", timeout=3600) as stream:
        for raw in stream:
            line = raw.decode().strip()
            if not line.startswith("data: ["):
                if line.startswith("event: end"):
                    break
                continue
            for ev in json.loads(line[6:]):
                now = time.perf_counter()
                if ev["type"] == "phase":
                    if last_phase:
                        phases[last_phase] = phases.get(last_phase, 0) + now - last_t
                    last_phase, last_t = ev["phase"], now
                if ev["type"] in ("done", "error", "cancelled"):
                    if last_phase:
                        phases[last_phase] = phases.get(last_phase, 0) + now - last_t
    wall = time.perf_counter() - t0
    job = call("GET", f"/api/jobs/{job_id}?plan=false")
    st = job["stats"]
    return {"wall": wall, "files": st.get("total", 0), "photos": st.get("photos", 0), "videos": st.get("videos", 0),
            "embedded": st.get("embedded", 0), "phases": phases, "usage": job.get("usage"), "status": job["status"]}


def main() -> None:
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--source", default="")
    ap.add_argument("--strategy", default="preset")
    ap.add_argument("--set", default="lifestyle")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--suite")
    a = ap.parse_args()
    BASE = a.base
    suite = (json.load(open(a.suite)) if a.suite else
             [{"label": f"{a.strategy} · {a.source or '/'}", "body": {"source": a.source, "strategy": a.strategy, "set_id": a.set}}])
    print("| Run | Files (photos/videos) | Analyzed now | Wall time | Files/s | Phases |")
    print("|---|---|---|---|---|---|")
    for item in suite:
        for i in range(a.runs):
            r = run(item["body"])
            ph = " · ".join(f"{k} {v:.1f}s" for k, v in r["phases"].items() if v >= 0.05)
            fps = r["files"] / r["wall"] if r["wall"] else 0
            label = item["label"] + (f" (run {i + 1})" if a.runs > 1 else "")
            print(f"| {label} | {r['files']} ({r['photos']}/{r['videos']}) | {r['embedded']} | {r['wall']:.1f}s | {fps:.0f} | {ph} |",
                  flush=True)


if __name__ == "__main__":
    main()
