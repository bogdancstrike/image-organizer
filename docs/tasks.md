# Tasks

Status: `[x]` done · `[ ]` open. Each task lists the specs it covers and its "done when" check.

## M1 Specs
- [x] T1 OpenSpec project + 7 capability specs, plan, acceptance criteria. *Done when* every requirement has an ID and a scenario.

## M2 Backend core
- [x] T2 `config.py` settings (DEP-4). *Done when* the defaults load with no env vars set.
- [x] T3 `scanner.py` discovery, skips, containment, metadata (SCAN-1..5). *Done when* `test_scanner.py` passes.
- [x] T4 `media.py` thumbnails, EXIF orientation/date, HEIC, video frames via ffmpeg, pHash, screenshot signal (ANL-1,3,4,5).
- [x] T5 `embedder.py` CLIP via fastembed + fake embedder for tests (ANL-2).
- [x] T6 `cache.py` SQLite cache keyed by path/size/mtime (ANL-6). *Done when* a re-run computes 0 embeddings.
- [x] T7 `dedupe.py` exact + near duplicates, keeper rules (DUP-1..4). *Done when* `test_dedupe.py` passes.
- [x] T8 `presets.py` 4 presets + vocabulary (CAT-1).
- [x] T9 `categories.py` custom sets CRUD + validation (CAT-2).
- [x] T10 `classify.py` zero-shot, screenshot override, auto KMeans, date (CAT-3..6).
- [x] T11 `planner.py` destinations, split media, `_Duplicates`, `Unsorted` (CAT-8, ORG-1).
- [x] T12 `organizer.py` apply move/copy, collisions, journal, undo, history (ORG-3..6). *Done when* the round-trip test passes.

## M3 Service
- [x] T13 `llm.py` Luna client: contact sheets, cluster naming in one call, batched assist, token accounting, fallbacks (CAT-5,7,9).
- [x] T14 `jobs.py` job pipeline thread, event log with replay (ORG-1,2).
- [x] T15 `main.py` REST + SSE + thumbnails + static UI (all API).
- [x] T16 API tests with a fake embedder (`test_api.py`).

## M4 Frontend
- [x] T17 Vite + React 19 + TS + Tailwind 4 + antd 6 scaffold, theme tokens, shadcn primitives (UI-6).
- [x] T18 Layout: header, stats, stage columns, cards, flower, responsive (UI-1).
- [x] T19 Canvas animation engine: pile, flight queue, tween, slots, reduced motion (UI-2).
- [x] T20 Settings drawer + folder tree (UI-3).
- [x] T21 Category editor modal (UI-4).
- [x] T22 Apply / undo / history / files drawer (UI-5).

## M5 Delivery
- [x] T23 Multi-stage Dockerfile, bundled model, non-root PUID/PGID (DEP-2).
- [x] T24 `docker-compose.yml`, healthcheck, volumes, `.env.example` (DEP-1,3,4,5).
- [x] T25 E2E check on a sample library: sort → apply → undo inside compose.
- [x] T26 README (logo, badges, GIF slot, quick start, contributing) + docs (architecture, configuration, API, categories, development).

## Backlog (good first issues)
- [ ] OCR signal (RapidOCR) to strengthen "Text & captions" and "Documents".
- [ ] Face detection + speech activity signal for "Talking to camera" videos.
- [ ] GPU image variant (onnxruntime-gpu).
- [ ] Larger CLIP models (SigLIP 2) as an option.
- [ ] Watch-folder mode (sort new downloads automatically).
- [ ] Desktop packaging (Tauri).
- [ ] i18n for UI and category names.
