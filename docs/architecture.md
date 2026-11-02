# Architecture

```mermaid
flowchart LR
  UI["React UI<br/>(antd + shadcn/ui + canvas)"] -- "REST" --> API
  API -- "SSE events" --> UI
  subgraph Container["Docker container"]
    API["FastAPI"] --> JM["JobManager<br/>(background thread)"]
    JM --> S[scan] --> A["analyze<br/>thread pool"] --> D[dedupe] --> C[categorize] --> P[plan]
    A --> CLIP["CLIP ViT-B/32<br/>ONNX · fastembed"]
    A --> FF["ffmpeg / Pillow / pillow-heif"]
    A <--> DB[("SQLite cache<br/>+ WebP thumbs")]
    C -. optional .-> LLM["OpenAI Luna<br/>reasoning: low"]
    API --> O["apply / undo<br/>JSON journals"]
  end
  O --> LIB[("/library<br/>your folders")]
  S --> LIB
```

## Backend packages

`app.main:create_app` remains the Docker entry point. Modules are grouped by responsibility:

| Package | Responsibility |
|---|---|
| `app.catalog` | Category definitions, presets and category-set management |
| `app.media` | Scanning, decoding, metadata and media inputs |
| `app.recognition` | Classification, person matching, text recognition, tags and prompt rules |
| `app.culling` | Quality signals, ranking, duplicates and social readiness |
| `app.organization` | Job orchestration, destinations and journaled file operations |
| `app.library` | Search, tag facets, geographic groups and trips |
| `app.infrastructure` | Configuration, SQLite cache/history, embeddings and optional OpenAI provider |

Package initializers stay small; import concrete modules explicitly. Internal Python import paths changed; HTTP
routes, stored data, environment variables and the Docker entry point remain compatible.

## Pipeline (one job)
| Step | What happens | Module |
|---|---|---|
| rules (rule strategy) | Vision AI compiles natural-language instructions into validated relative paths before any analysis. Dates are frozen at sort start. | `recognition/rules.py`, `infrastructure/llm.py` |
| scan | Walk the chosen folder (optionally recursively). Hidden folders, the output folder and `_Duplicates` are skipped. | `media/scanning.py` |
| analyze | Decode with draft-mode JPEG, EXIF orientation and date, HEIC. Video keyframes come from ffmpeg (20/50/80%). SHA-256, pHash, screenshot signal, 160 px WebP thumbnail, CLIP embedding (videos: mean of frames). Results are cached by (path, size, mtime). | `media/decoding.py`, `infrastructure/embeddings.py`, `infrastructure/cache.py` |
| dedupe | Union-find over SHA-256 matches plus pHash ≤ 4 with CLIP cosine ≥ 0.90. Keeper = most pixels, then size, then oldest. | `culling/duplicates.py` |
| categorize | Preset/custom: zero-shot `softmax(100·cos)` over averaged prompt embeddings, a screenshot rule, per-category floors, optional AI assist. Auto: KMeans + silhouette, named by Luna or the vocabulary. Date: capture date. | `recognition/classification.py`, `infrastructure/llm.py` |
| plan | Destination per file: `<folder>/<output>/Photos|Videos/<Category>/`; AI rules use their explicit relative paths without media prefixes | `organization/planner.py` |
| apply / undo | Move or copy with collision-safe names, a journal written as it goes, reverse replay, and cleanup of the folders it created | `organization/operations.py` |

Each step emits events (`phase`, `scanned`, `file`, `progress`, `stats`, `categories`, `assign`, `done`) into an append-only log.
`GET /api/jobs/{id}/events` streams it as Server-Sent Events, and late subscribers get a replay.

## The animation
`frontend/src/anim/engine.ts` draws everything on one `<canvas>` laid over the stage:
- every `file` event adds a sprite with a pre-rendered "polaroid" tile (frame and shadow baked in, so one `drawImage` per sprite per frame);
- the pile is stored in polar coordinates and re-projected each frame, so it follows layout changes;
- `assign` events queue flights. Flights are released at `n / (60 · 5s)` per frame, so every run lasts about 5 s, and they follow an eased arc to the next slot in the target card (whose rect is read from the DOM each frame);
- `prefers-reduced-motion` makes sprites jump straight to their slots;
- themes are CSS variables; the engine re-reads them and re-renders tiles when the theme changes.

## Why these choices
- **ONNX CLIP instead of PyTorch**: CPU by default, optional CUDA runtime, a much smaller image, the model is bundled, and it works offline.
- **The LLM is optional and called rarely**: one request names every cluster; assist sends batched low-detail thumbnails. The explicit AI-rules strategy uses one compilation request plus all eligible thumbnails.
- **SSE instead of WebSockets**: the stream is one-way, and replay is trivial.
- **Plan → apply → journal**: you can trust it with your real folders.

## Culling recommendations

`culling/ranking.py` adapts weights to detected or explicitly selected photography profiles. Technical focus/clipping/noise,
face expressions, geometry and paired CLIP/SigLIP presentation prompts form absolute component scores. These are
blended with within-shoot and scene rankings. Keeper thresholds, Review stars and XMP ratings share this score.
Selection covers scenes, suppresses near-duplicates and leaves the quota unfilled when candidates are weak.
Quality cache version 5 stores per-face eye focus and the expanded image-quality signals. See [research notes](culling-research.md).

## Device selection

Compose extends `docker/compose.${DEVICE}.yml` (CPU default) to choose the Docker target and optional NVIDIA
reservation. The embedder selects explicit execution providers for both text and image towers and validates CUDA
activation. Singleton identity includes model, device and cache path; cache files remain separated by model.

## Dependency boundaries

This is a modular monolith: one deployable application with cohesive domain packages. `app.main` wires the runtime
and mounts HTTP adapters from `app.api.routes`. API request validation lives in `app.api.schemas`; each router receives
an explicit per-application runtime context, avoiding global application services shared between factory instances.

Culling decisions live in `app.culling.service`, independently of job lifecycle, HTTP and persistence. Classification
uses the embedding protocol in `app.recognition.ports`; ONNX, MediaPipe, YuNet/SFace and RapidOCR implementations live
in infrastructure. Category validation/preset construction is separated from its SQLite repository. Library reads go
through public cache repository methods rather than private database connections.

`tests/test_architecture.py` prevents core modules from importing HTTP, storage or model-loading adapters and verifies
that separate application factories keep settings and libraries isolated. Numerical libraries are permitted in core
algorithms. Application workflows coordinate IO adapters; this does not introduce microservices or generic repository
frameworks. The stable Docker entry point remains `app.main:create_app`.
