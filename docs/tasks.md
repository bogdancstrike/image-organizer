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

## M6 Pro & polish (done)
- [x] T27 Quality signals, tiled face detection, culling strategy, rejects overlay (QC-1..6).
- [x] T28 Score & stars, best-of-burst, Maybe, main-face rule, exposure thresholds (QC-2..5).
- [x] T29 RAW decoding, RAW+JPEG pairing and sidecars moving together (QC-7).
- [x] T30 Context-aware auto (theme, focus, granularity, facet names; AI with overview + instructions).
- [x] T31 URL tabs: Sort / Review (plan table + reassign) / Categories (editable presets) / History / Settings.
- [x] T32 Lightbox and video player, themes Graphite/Light/Lavender, aperture logo, responsive drawers and modals.
- [x] T33 Per-run AI settings (model, effort, naming/assist instructions, batch), `gpt-6-luna` default.
- [x] T34 Perf: thread caps (KMeans 13× faster), workers `min(8, CPUs)`, memory peak 6.1 → 2.2 GB, keyframe-only video decoding.
- [x] T35 Benchmarks + README performance & hardware section.

## M7 Guided & smarter (done)
- [x] T36 Recipes + `/api/suggest`: the app samples the folder and recommends how to sort it (pre-selected).
- [x] T37 By person: YuNet + SFace identities, agglomerative clustering, avatars, rename folders.
- [x] T38 SigLIP 2 model option with per-model cache; OCR signal (RapidOCR) + searchable text.
- [x] T39 i18n: en, ro, es, de, fr (main surfaces; English fallback).
- [x] T40 Boudoir session preset (poses & light); benchmarks on a 1,029-photo shoot.

## M8 Rules, GPU, recommendations and validation
- [x] T41 AI prompt rules: compile free-text instructions, validate nested/date paths, classify thumbnails, then Review / Apply / Undo.
- [x] T42 Optional NVIDIA GPU image and Compose runtime, selected through `DEVICE=cpu|gpu`; verified CLIP and SigLIP 2 on RTX 3080.
- [x] T43 Stronger Picks and Keepers: portrait/fashion/landscape profiles; technical, expression, composition, lighting and presentation signals; absolute + shoot/scene ranking; scene coverage and near-duplicate suppression.
- [x] T44 Expression and group-shot scoring, per-face eye focus, main-subject preference, explained recommendations; keeper thresholds and XMP use the same score.
- [x] T45 Quick settings and Sort recipe selection agree, including manual strategy changes.
- [x] T46 Backend and frontend coverage gates: at least 90% line coverage separately, all application source measured, HTML/JSON reports and CI.

## Backlog (good first issues)
- [x] OCR signal (RapidOCR) to strengthen "Text & captions" and "Documents".
- [ ] Speech-activity signal for "Talking to camera" videos.
- [x] Write star ratings / labels to XMP for Lightroom & Capture One.
- [ ] Local vision-LLM engine (vLLM, OpenAI-compatible) for zero-token AI.
- [x] GPU image variant (FastEmbed GPU + ONNX Runtime CUDA; `DEVICE=gpu` in `.env`, CPU default).
- [x] Larger CLIP models (SigLIP 2) as an option.
- [ ] Watch-folder mode (sort new downloads automatically).
- [ ] Desktop packaging (Tauri).
- [ ] Complete i18n for all UI and category names (five languages already cover main surfaces).
- [ ] Cleanup assistant and storage report.
- [ ] Dedicated portfolio picker.
- [ ] Licensed expert-rated culling benchmark: compare recommendations with multiple photographers per genre.

- [x] T47 Reliable identity anchors, evidence-gated pose consolidation, co-occurrence safeguards and ambiguous-view matching; read-only 1,029-photo regression returned four representative people instead of 29.
- [x] T48 Adjustable decimal Picks/Keepers bands in Quick settings (4.5/4.0 defaults), Similar alternatives, multiscale detail/balance/separation, folder score ascending/descending (descending default).

- [x] T49 Accessible hover/focus explanations for photo badges and status icons.
- [x] T50 Local automatic tags, scoped exact tag facets and hybrid search, with Apply/Undo metadata continuity.
- [x] T51 Social Media preset and Cull controls: crop formats, thumbnail clarity, visual story and optional prompt relevance.
- [x] T52 Expanded culling methods: Tenengrad, dHash guard, native analysis face focus, novelty, Pareto alternatives and burst margins; 30 article ideas mapped to code/tests.
- [x] T53 Compare 2–4 originals with synchronized pan/zoom, face crops and destination overrides.
- [x] T54 Compact folder score toolbar and collapsible Quick settings/full settings categories.

- [x] T55 Cohesive backend packages, inward domain dependencies, route factories and architecture guards.
- [x] T56 Persistent full-screen image/score panel, desktop joined edges, mobile stacking and one Winner recommendation.
- [x] T57 Compound library-query evidence gates and removal of forced minimum results.
- [x] T58 Shoot-local appearance classifier, multi-view consensus and sequence support for partial/faceless views; ambiguous views remain reviewable.
- [x] T59 Decision provenance for categories, scores, duplicate keepers, recoverable trash and manual overrides; previews survive Apply/restart/Undo.
- [x] T60 Optional offline LAION aesthetic model for Social Media, exact encoder compatibility, CPU inference, versioned cache and bounded SigLIP shortlist.
