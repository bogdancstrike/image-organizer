# Configuration

Everything is configured with environment variables, read by `docker compose` from `.env` (see `.env.example`).
Every variable is optional.

| Variable | Default | Description |
|---|---|---|
| `LIBRARY_PATH` | `$HOME` | Host folder mounted read-write at `/library`. The UI can browse and organize anything under it. |
| `LIBRARY_NAME` | `Library` | Fallback name for the headline when no folder name is known |
| `PORT` | `8080` | Host port of the web UI and API |
| `PUID` / `PGID` | `1000` | User and group the app runs as, so moved files keep your ownership (`id -u`, `id -g`) |
| `OPENAI_API_KEY` | *(empty)* | Turns on AI cluster naming (Auto mode) and AI assist. Without it everything runs locally. |
| `OPENAI_MODEL` | `gpt-6-luna` | Any vision-capable model on the Responses API |
| `OPENAI_REASONING_EFFORT` | `low` | `low` keeps calls fast and cheap |
| `OUTPUT_DIR_NAME` | `Organized` | Default name of the subfolder that holds sorted folders (the UI can override it per run) |
| `WORKERS` | `min(8, CPUs)` | Threads for decoding, thumbnails and quality checks |

## Volumes
| Container path | Purpose |
|---|---|
| `/library` | Your folders (bind mount of `LIBRARY_PATH`) |
| `/data` | `cache.db` (analysis cache), `thumbs/`, `journals/` (undo), `category_sets.json`. Safe to delete; it only costs a re-analysis. |

## Privacy and cost of AI
- With no key set, **nothing leaves your machine**. CLIP runs locally on the CPU (ONNX).
- **Auto mode** sends one request per sort: a 384×256 contact sheet per discovered group, at `detail: low`.
  A typical run costs about 1–2k tokens in total.
- **AI assist** (opt-in) sends only the *uncertain* files, as 160 px thumbnails, 12 per request, at most 200 per sort.
- The key is used only by the backend. The browser only learns `ai_available: true|false`.

## Per-run options (UI → API)
| Option | Default | Notes |
|---|---|---|
| `output_dir` | `OUTPUT_DIR_NAME` | `""` = category folders directly inside the chosen folder |
| `recursive` | `true` | Include files in subfolders |
| `split_media` | `true` | Separate `Photos/` and `Videos/` |
| `min_confidence` | `0.30` | Below it, a file goes to `Unsorted` |
| `near_duplicates` | `true` | pHash ≤ 4 **and** CLIP cosine ≥ 0.90 |
| `ai_assist` | `false` | Needs a key |
| `max_clusters` | `12` | Auto mode upper bound; the best k is picked by silhouette score |
| `date_granularity` | `month` | `year`, `month` or `day` |
