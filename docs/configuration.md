# Configuration

Everything is configured with environment variables, read by `docker compose` from `.env` (see `.env.example`).
Every variable is optional.

| Variable | Default | Description |
|---|---|---|
| `LIBRARY_PATH` | `$HOME` | Host folder mounted read-write at `/library`. The UI can browse and organize anything under it. |
| `LIBRARY_NAME` | `Library` | Fallback name for the headline when no folder name is known |
| `PORT` | `8080` | Host port of the web UI and API |
| `PUID` / `PGID` | `1000` | User and group the app runs as, so moved files keep your ownership (`id -u`, `id -g`) |
| `OPENAI_API_KEY` | *(empty)* | Required for AI prompt rules; enables optional Auto naming and assist. Local modes work without a key. |
| `OPENAI_MODEL` | `gpt-6-luna` | Any vision-capable model on the Responses API |
| `OPENAI_REASONING_EFFORT` | `low` | `low` keeps calls fast and cheap |
| `OUTPUT_DIR_NAME` | `Organized` | Default name of the subfolder that holds sorted folders (the UI can override it per run) |
| `DEVICE` | `cpu` | `cpu` or `gpu`; selects the CPU or NVIDIA image and embedding providers |
| `WORKERS` | `min(8, CPUs)` | Threads for decoding, thumbnails and quality checks |

## Volumes
| Container path | Purpose |
|---|---|
| `/library` | Your folders (bind mount of `LIBRARY_PATH`) |
| `/data` | `cache.db` (analysis cache), `thumbs/`, `journals/` (undo), `category_sets.json`. Safe to delete; it only costs a re-analysis. |

## Privacy and cost of AI
- With no key set, **nothing leaves your machine**. CLIP/SigLIP run locally on the selected CPU or GPU (ONNX).
- **Auto mode** sends one request per sort: a 384×256 contact sheet per discovered group, at `detail: low`.
  A typical run costs about 1–2k tokens in total.
- **AI assist** (opt-in) sends only the *uncertain* files, as 160 px thumbnails, 12 per request, at most 200 per sort.
- The key is used only by the backend. The browser only learns `ai_available: true|false`.

- **AI rules** sends one text request to compile the prompt, followed by batches of thumbnails for all non-duplicate files. This strategy requires a key; failures stop the job without applying a partial plan.

## Per-run options (UI → API)
| Option | Default | Notes |
|---|---|---|
| `output_dir` | `OUTPUT_DIR_NAME` | `""` = category folders directly inside the chosen folder |
| `recursive` | `true` | Include files in subfolders |
| `split_media` | `true` | Separate `Photos/` and `Videos/` |
| `min_confidence` | `0.30` | Below it, a file goes to `Unsorted` |
| `near_duplicates` | `true` | pHash ≤ 4 **and** CLIP cosine ≥ 0.90 |
| `rules_prompt` | `""` | Required non-empty instructions for `strategy: "rules"`, up to 4,000 characters |
| `quality.pick_profile` | `auto` | Auto, portrait, fashion, landscape or general; adapts keeper and top-pick ranking locally |
| `quality.pick_min_rating` | `4.5` | Picks need at least this decimal rating / 5; adjustable in Quick settings |
| `quality.keeper_min_rating` | `4.0` | Keepers need this rating and stay below Picks; 1–5 and no higher than Picks |
| `quality.write_xmp` | `false` | Export stars plus Green for picks/Red for rejects on Apply; computes scores even with reject checks off |
| `ai_assist` | `false` | Needs a key |
| `max_clusters` | `12` | Auto mode upper bound; the best k is picked by silhouette score |
| `date_granularity` | `month` | `year`, `month` or `day` |

## CPU or NVIDIA GPU

Set `DEVICE=cpu` (the default) or `DEVICE=gpu` in `.env`, then run `docker compose up -d --build`.
Compose selects the matching build target and reserves one NVIDIA GPU only in GPU mode. GPU mode requires
an NVIDIA driver and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
on the host; the image bundles CUDA and cuDNN. CPU mode needs neither.

CLIP and SigLIP 2 image/text embeddings use the GPU. Decoding, MediaPipe quality checks, face identities, OCR,
and clustering continue on the CPU. Cached embeddings can be reused across devices. GPU initialization failures
are reported instead of silently falling back to CPU. `/api/health` reports the configured `device`.

For a local Python GPU environment, replace `fastembed`/`onnxruntime` with `fastembed-gpu==0.9.1` and
`onnxruntime-gpu[cuda,cudnn]==1.23.2`, then set `DEVICE=gpu`. Do not install both ONNX Runtime distributions together.
See [FastEmbed GPU](https://qdrant.github.io/fastembed/examples/FastEmbed_GPU/) and
[ONNX Runtime CUDA](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html) for runtime requirements.

## Person grouping

YuNet/SFace identity anchors require sufficiently large, confident faces with readable eye/nose geometry.
Average-link clustering starts with the documented SFace pair threshold. For 12–2,500 anchors, a silhouette
improvement can consolidate pose/lighting fragments; reliable co-occurring faces guard against merging distinct people.
Higher similarity settings above 0.45 retain the stricter cut. Partial faces can match an existing gallery with
a confidence margin, but cannot create identities. Uncertain face matches stay in Other people. Appearance matching
for faceless photos remains an optional heuristic, not proof of identity. The face cache refreshes once after upgrade.
