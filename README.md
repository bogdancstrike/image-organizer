<div align="center">

<img src="frontend/public/logo.svg" width="112" alt="Auto Image Organizer logo" />

# Auto Image Organizer

**Turn a messy photo folder into beautifully organized albums. Locally, in seconds, with an undo button.**

Sort by what's *in* the photos, cull a shoot like a pro (blurry · eyes closed · best of burst),
and watch every thumbnail fly into its folder.

[![License: MIT](https://img.shields.io/badge/license-MIT-ec7fae?style=flat-square)](LICENSE)
[![Docker Compose](https://img.shields.io/badge/deploy-docker%20compose-2496ED?style=flat-square&logo=docker&logoColor=white)](#-quick-start)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](backend)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](backend)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](frontend)
[![antd 6](https://img.shields.io/badge/antd-6-1677ff?style=flat-square&logo=antdesign&logoColor=white)](frontend)
[![Runs offline](https://img.shields.io/badge/AI-optional%20%C2%B7%20runs%20offline-18181b?style=flat-square)](#-ai-is-optional)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-a1a1aa?style=flat-square)](CONTRIBUTING.md)
[![GitHub stars](https://img.shields.io/github/stars/bogdancstrike/image-organizer?style=flat-square&color=ec7fae)](https://github.com/bogdancstrike/image-organizer/stargazers)

[Quick start](#-quick-start) · [Features](#-features) · [Screenshots](#-screenshots) · [For photographers](#-for-photographers-culling) · [Deploy](#-deployment) · [Docs](#-documentation)

<br/>

<img src="docs/assets/screenshot-flying.png" alt="Thumbnails flying from the pile into their folders" width="100%" />

</div>

---

## ✨ Why

Your *Downloads*, your phone dump, last weekend's shoot: thousands of files called `IMG_4821.JPG`.
**Auto Image Organizer** looks at every photo and video, understands what it shows, and proposes a clean folder
structure. Nothing moves until you press **Apply**, and every apply can be **undone**.

- 🧠 **Understands content.** CLIP sorts *outfits*, *mountains*, *studio light*, *food & cafés*, *screenshots* … no tags needed.
- 📸 **Built for photographers.** Culling with blur, eyes-closed and exposure checks, best-of-burst, stars, and RAW + JPEG pairs.
- 🔒 **Private by default.** Everything runs on your machine. AI is an optional, token-frugal helper.
- ↩️ **Safe.** You get a plan, then Apply, and a journal records every move, so Undo restores every file.
- 🌸 **Delightful.** A pile of polaroids flies into folder cards, in seven themes (Graphite dark by default).

## 🚀 Quick start

```bash
git clone https://github.com/bogdancstrike/image-organizer.git && cd image-organizer
cp .env.example .env            # optional: OPENAI_API_KEY, LIBRARY_PATH …
docker compose up -d --build    # first build bundles the models (~3 min)
```

Open **http://localhost:8080**, click the folder name in *"Sorting my **…** folder"*, pick a folder, and press **Sort**.

> 💡 No photos at hand? `./scripts/download-samples.sh` (landscapes, duplicates, clips) and
> `python3 scripts/download-portraits.py` (200 openly licensed portraits & outfits) fill `./sample-library/`.

## 🧩 Features

### Organize any way you like

| Mode | What you get | Good for |
|---|---|---|
| **Preset** | 13 ready-made, **editable** folder sets | Instant results |
| **My categories** | Your own folders, each described in a few words (and *Photos-only / Videos-only*) | Your Instagram system, client workflows |
| **Auto-discover** | Groups found automatically, named by **what makes them different** inside your folder | Unknown dumps, a studio shoot, a wedding |
| **By date** | `2025/07 - July` from EXIF / video metadata | Archives |
| **Cull** | Keepers · Smiling · Maybe · Blurry · Eyes closed · Too dark/bright · Burst extras | Photographers |

**Presets:** Lifestyle · People & Style · Photoshoot themes (wedding, halloween, moto, pool, studio …) · Wedding day ·
Instagram creator · Travel · Creator · Family & kids · Events · Real estate · Nature & wildlife · Food & product · Documents.
Every preset can be edited from **/categories** and reset to its default.

**Auto-discover understands context.** It detects what the folder *is* (e.g. *Trash the dress · mountains*), lets you choose
**what to group by** (scene, framing & pose, outfit, lighting, subject) and **how finely** (coarse / normal / fine), then names
groups like *Full-body · Golden hour* or *Close-up · Low-key*, not "Wedding" fifteen times.

### 📸 For photographers: culling

| Check | How |
|---|---|
| **Blurry / missed focus** | Laplacian sharpness measured **on faces** when present (bokeh is fine), else on the sharpest tile |
| **Eyes closed** | MediaPipe Face Landmarker blendshapes, on **any face** or only the **main subject** |
| **Smiles** | Smile score per face; *Smiling* gets its own folder |
| **Exposure** | Too dark / too bright, with adjustable thresholds |
| **Best of burst** | Near-identical frames shot seconds apart: keep the best, set the rest aside |
| **Score & stars** | 0–100 keeper score and 1–5 ★ for every photo; *Maybe* for keepers under your star bar |
| **RAW workflow** | `.ARW .CR2 .CR3 .NEF .DNG .RAF …` read through the embedded preview; **RAW + JPEG pairs and `.xmp` sidecars move together** |

Use **Cull** on its own, or switch on *quality checks* with any other mode to set rejects aside in `_Rejects/<reason>`.

### Safe by design
- **Plan → Review → Apply → Undo.** Review the plan in a sortable, filterable table, open any photo full-size, and **reassign** files (or a whole selection) before applying.
- Move **or** copy. Collisions become `name (1).jpg`, and a journal makes undo work even after a restart.
- Duplicates (byte-identical **and** resized or re-saved copies) go to `_Duplicates`. Nothing is ever deleted.

### Fast & frugal
- CLIP ViT-B/32 on **ONNX/CPU**: about 100 photos in about 5 s on first run, and **re-runs are instant** thanks to the analysis cache.
- Videos: keyframe-only decoding at 336 px with sampled hashing, so a 60 s 1080p clip takes **0.3 s**. Photos are analyzed first.
- 40+ formats: JPEG, PNG, HEIC/HEIF, AVIF, **JPEG XL**, WebP, TIFF, PSD, JPEG 2000, camera RAW · MP4, MOV, MKV, MTS/M2TS, AVI, WMV, …

### 🤖 AI is optional
Without a key, everything works offline. With `OPENAI_API_KEY`, the app uses **`gpt-6-luna`** (`reasoning: low`):
- **Auto naming:** *one* request per sort (small contact sheets at `detail: low`, about 1–2k tokens).
- **AI assist** (opt-in): only *uncertain* files, 12 thumbnails per request.
- Model, reasoning effort and extra instructions (your own "system prompt") are editable in **Settings → AI**.

## 🖼 Screenshots

| Sorted | Review & edit the plan |
|---|---|
| <img src="docs/assets/screenshot-dark.png" alt="Sorted folders in the Graphite theme" /> | <img src="docs/assets/screenshot-review.png" alt="Review table" /> |
| **Full-size viewer** | **Categories & editable presets** |
| <img src="docs/assets/screenshot-lightbox.png" alt="Lightbox" /> | <img src="docs/assets/screenshot-categories.png" alt="Categories" /> |
| **Settings** | **Blossom theme** |
| <img src="docs/assets/screenshot-settings.png" alt="Settings page" /> | <img src="docs/assets/screenshot-sorting.png" alt="Pink theme" /> |

## ⚙️ How it works

<img src="docs/assets/diagram-flow.png" alt="Pick a folder, sort, review, apply, undo" width="100%" />

<img src="docs/assets/diagram-architecture.png" alt="Architecture" width="100%" />

One container: **FastAPI** runs a background pipeline (scan → analyze → quality → dedupe → categorize → plan) and streams
progress to the **React** UI over Server-Sent Events. A canvas engine animates every file from the pile into its folder card.

## 🐳 Deployment

```bash
docker compose up -d --build        # start / update
docker compose logs -f              # logs
docker compose run --rm organizer pytest -q   # tests inside the image
```

| Variable | Default | |
|---|---|---|
| `LIBRARY_PATH` | `$HOME` | Host folder the app may browse & organize (mounted read-write at `/library`) |
| `PORT` | `8080` | Web UI / API port |
| `PUID` / `PGID` | `1000` | Files are moved as this user |
| `OPENAI_API_KEY` | – | Optional AI naming & assist |
| `OPENAI_MODEL` | `gpt-6-luna` | Any vision-capable model on the Responses API |
| `OUTPUT_DIR_NAME` | `Organized` | Default subfolder for sorted folders (changeable per run) |

> ⚠️ The app has **no login** and can move files under `LIBRARY_PATH`. Keep it on `localhost` or behind your own
> authenticating reverse proxy, and narrow `LIBRARY_PATH` (e.g. `~/Pictures`) if you prefer.

Full list: [docs/configuration.md](docs/configuration.md).

## 📚 Documentation

| | |
|---|---|
| [Getting started](docs/getting-started.md) | Folders, modes, apply & undo, themes |
| [Organizing modes & categories](docs/categories.md) | Presets, custom sets, auto-discover, culling |
| [Configuration](docs/configuration.md) | Environment, volumes, AI privacy & cost |
| [Architecture](docs/architecture.md) | Pipeline, animation engine, design decisions |
| [API](docs/api.md) | REST + SSE reference (`/docs` for Swagger) |
| [Development](docs/development.md) | Dev loop, tests, project layout |
| [Specs (OpenSpec)](docs/openspec/project.md) · [Plan](docs/implementation-plan.md) · [Tasks](docs/tasks.md) · [Acceptance](docs/acceptance-criteria.md) | How it's built |

## 🛠 Development

```bash
# backend (Python 3.12 + ffmpeg)
cd backend && pip install -r requirements.txt && pytest -q
LIBRARY_ROOT=$HOME DATA_DIR=../data uvicorn --factory app.main:create_app --reload --port 8000
# frontend (Node 22+)
cd frontend && npm install && npm run dev      # http://localhost:5173, proxies /api
```

**Stack:** FastAPI · fastembed (CLIP ONNX) · MediaPipe · Pillow / pillow-heif / rawpy · ffmpeg · scikit-learn · SQLite ·
React 19 · TypeScript · Vite · antd 6 · Tailwind 4 · shadcn/ui-style components · Canvas 2D.

## 🗺 Roadmap

Write star ratings to XMP for Lightroom · face clustering ("by person") · local vision LLM engine (vLLM, zero tokens) ·
watch-folder mode · GPU image · desktop app (Tauri) · i18n. See [docs/tasks.md](docs/tasks.md), and ideas are welcome!

## 🤝 Contributing

PRs, presets, translations and bug reports are very welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md).
Adding a preset is a perfect first PR ([`backend/app/presets.py`](backend/app/presets.py)).

If this saved you an afternoon of dragging files around, **please ⭐ the repo**: it helps others find it.

## 📄 License

[MIT](LICENSE) © bogdancstrike. CLIP weights © OpenAI (MIT), MediaPipe © Google (Apache-2.0).
