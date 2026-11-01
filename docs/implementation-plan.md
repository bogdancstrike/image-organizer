# Implementation Plan

## Architecture

```
            ┌────────────────────────── Docker container ───────────────────────────┐
 Browser ──►│ FastAPI (uvicorn)                                                     │
  React UI  │  ├─ /            static React build (Vite)                            │
  (SSE)  ◄──│  ├─ /api/*       REST + SSE                                           │
            │  └─ JobManager ─► pipeline thread                                     │
            │        scan ─► analyze (thread pool) ─► dedupe ─► categorize ─► plan  │
            │                    │  Pillow/pillow-heif, ffmpeg, imagehash           │
            │                    │  CLIP ViT-B/32 (fastembed, ONNX, CPU)            │
            │                    └─ SQLite cache  /data/cache.db, thumbs /data/thumbs│
            │        categorize ─► zero-shot │ KMeans auto │ date │ (Luna assist)   │
            │        apply/undo ─► journals /data/journals/*.json                   │
            └──────────────┬────────────────────────────────────────────────────────┘
                   /library (bind mount)                 api.openai.com (optional)
```

## Backend modules (`backend/app`)
| Module | Responsibility | Specs |
|---|---|---|
| `config.py` | Settings from the environment | DEP-4 |
| `scanner.py` | Walk folders, path containment, metadata | SCAN-* |
| `media.py` | Decoding, HEIC, EXIF orientation and date, ffmpeg frames, thumbnails, pHash, screenshot signal | ANL-1,3,4,5 |
| `embedder.py` | `Embedder` protocol + `ClipEmbedder` (fastembed). Tests inject a fake one | ANL-2 |
| `cache.py` | SQLite cache of analysis results (embeddings stored as float32 blobs) | ANL-6 |
| `presets.py` | Preset category sets + auto-naming vocabulary | CAT-1, CAT-5 |
| `categories.py` | Custom set storage and validation | CAT-2 |
| `classify.py` | Zero-shot, screenshot override, auto-clustering, date strategy | CAT-3..6 |
| `llm.py` | Luna client: `name_clusters`, `assist_classify`, token accounting, contact sheets | CAT-5,7,9 |
| `dedupe.py` | SHA + pHash union-find, keeper selection | DUP-* |
| `planner.py` | Destinations and the plan | CAT-8, ORG-1 |
| `organizer.py` | Apply, journal, undo, history | ORG-3..6 |
| `jobs.py` | Job state, event log with replay, pipeline thread | ORG-1,2 |
| `main.py` | FastAPI routes, SSE, static files | all |

## API
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | status, `ai_available`, model |
| GET | `/api/folders?path=` | subfolders + media counts |
| GET | `/api/presets` | built-in category sets |
| GET/PUT/DELETE | `/api/category-sets[/{id}]` | custom sets |
| POST | `/api/jobs` | start a sort `{source, strategy, set_id, options}` |
| GET | `/api/jobs/{id}` | job snapshot (plan, stats, warnings) |
| GET | `/api/jobs/{id}/events` | SSE stream with replay |
| GET | `/api/thumbs/{file_id}` | WebP thumbnail |
| POST | `/api/jobs/{id}/apply` | `{mode: move|copy}` → run |
| GET | `/api/runs` | history |
| POST | `/api/runs/{id}/undo` | undo |

## Frontend (`frontend/src`)
- `api.ts`: typed fetch helpers and the SSE subscription.
- `store.ts`: a small React state reducer for the job (files, categories, assigns, stats).
- `anim/Stage.tsx` + `anim/engine.ts`: the canvas overlay, sprites, pile layout, flight queue, tweening,
  and slot lookup from the card DOM rects (`data-cat-id` refs).
- `components/`: `Header`, `Stats`, `CategoryCard`, `Flower`, `SettingsDrawer`, `CategoryEditor`,
  `HistoryDrawer`, `FilesDrawer`, `Logo`.
- `components/ui/`: shadcn-style `button`, `card`, `badge`.

## Key decisions
1. **CLIP through fastembed/ONNX, not PyTorch**: the image is about 700 MB instead of about 5 GB, it runs on CPU, and the model is bundled.
2. **The LLM only where it pays**: one request names every cluster; assist sends batches of 12 thumbnails at
   `detail: low`. Default model `gpt-5.6-luna` (measured at about 1.5 s per call with 0 reasoning tokens at `effort=low`).
3. **SSE instead of WebSocket**: one-way events and simple replay.
4. **Canvas sprites instead of DOM elements**: 1,000+ animated thumbnails at 60 fps.
5. **Plan, then apply, with a journal**: users can trust the tool with their real folders.

## Milestones
1. M1 Specs & docs (this folder).
2. M2 Backend core: scanner, media, embedder, cache, dedupe, classify, planner, organizer + unit tests.
3. M3 Jobs, API, SSE, LLM integration.
4. M4 Frontend: layout, theme, animation, drawers, editor.
5. M5 Docker + compose, end-to-end run on a sample library, README + docs.
