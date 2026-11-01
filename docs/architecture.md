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

## Pipeline (one job)
| Step | What happens | Module |
|---|---|---|
| scan | Walk the chosen folder (optionally recursively). Hidden folders, the output folder and `_Duplicates` are skipped. | `scanner.py` |
| analyze | Decode with draft-mode JPEG, EXIF orientation and date, HEIC. Video keyframes come from ffmpeg (20/50/80%). SHA-256, pHash, screenshot signal, 160 px WebP thumbnail, CLIP embedding (videos: mean of frames). Results are cached by (path, size, mtime). | `media.py`, `embedder.py`, `cache.py` |
| dedupe | Union-find over SHA-256 matches plus pHash ≤ 4 with CLIP cosine ≥ 0.90. Keeper = most pixels, then size, then oldest. | `dedupe.py` |
| categorize | Preset/custom: zero-shot `softmax(100·cos)` over averaged prompt embeddings, a screenshot rule, per-category floors, optional AI assist. Auto: KMeans + silhouette, named by Luna or the vocabulary. Date: capture date. | `classify.py`, `llm.py` |
| plan | Destination per file: `<folder>/<output>/Photos|Videos/<Category>/` | `planner.py` |
| apply / undo | Move or copy with collision-safe names, a journal written as it goes, reverse replay, and cleanup of the folders it created | `organizer.py` |

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
- **ONNX CLIP instead of PyTorch**: CPU-only, a much smaller image, the model is bundled, and it works offline.
- **The LLM is optional and called rarely**: one request names every cluster; assist sends batched low-detail thumbnails.
- **SSE instead of WebSockets**: the stream is one-way, and replay is trivial.
- **Plan → apply → journal**: you can trust it with your real folders.
