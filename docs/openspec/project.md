# Project: Auto Image Organizer

## Purpose
Auto Image Organizer turns a messy folder of photos and videos (Downloads, camera dumps, trip exports)
into a tidy tree of named folders. It recognizes what each file shows, groups it into
categories, finds duplicates, and moves (or copies) everything into place. Every run can be undone.
The sorting is shown as a live animation: thumbnails start in one pile and fly into their folders.

## Principles
1. **Local first.** Media never leaves the machine unless the user turns on AI assist.
   With AI assist on, only small low-resolution thumbnail grids are sent.
2. **Safe by default.** Analysis produces a *plan*. Files are touched only on an explicit *Apply*.
   Nothing is ever hard-deleted, and every apply writes an undo journal.
3. **Cheap and fast.** CLIP embeddings run locally on CPU (ONNX). The LLM (OpenAI *Luna*,
   `reasoning: low`) is called only where it clearly helps, with batched images at `detail: low`.
4. **Many ways to organize.** Built-in presets, user-defined categories, automatic discovery, and by date.

## Tech stack
| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Vision embeddings | CLIP ViT-B/32 via `fastembed` (ONNX Runtime, CPU) |
| LLM (optional) | OpenAI Responses API, model `gpt-5.6-luna` (configurable), `reasoning.effort=low` |
| Media | Pillow, pillow-heif, ffmpeg/ffprobe, imagehash |
| Clustering | scikit-learn (KMeans + silhouette) |
| Storage | SQLite (analysis cache), JSON (undo journals), WebP thumbnails |
| Frontend | React 19, TypeScript, Vite, antd 6, Tailwind CSS 4, shadcn/ui-style components, Canvas 2D animation |
| Delivery | Docker multi-stage image, `docker compose` |

## Glossary
- **Library**: the folder being organized, mounted into the container at `/library`.
- **Source folder**: the subfolder of the library chosen for a run (default: the library root).
- **Category set**: an ordered list of categories, each with a name and optional text prompts.
- **Strategy**: how files are mapped to categories: `preset`, `custom`, `auto`, `date`.
- **Plan**: the list of `{file, category, destination}` produced by analysis. Nothing is touched yet.
- **Run / Journal**: one applied plan and its record of moves, used for undo.

## Capabilities (specs)
| Spec | Summary |
|---|---|
| [library-scanning](specs/library-scanning/spec.md) | Discover media files and read their metadata |
| [media-analysis](specs/media-analysis/spec.md) | Thumbnails, embeddings, hashes, and caching |
| [categorization](specs/categorization/spec.md) | Presets, custom categories, auto-discovery, by date, AI assist |
| [duplicate-detection](specs/duplicate-detection/spec.md) | Exact and near-duplicate detection, and picking which copy to keep |
| [organize-apply-undo](specs/organize-apply-undo/spec.md) | Plans, applying moves or copies, the journal, undo |
| [web-ui](specs/web-ui/spec.md) | The single-page UI and the sorting animation |
| [deployment](specs/deployment/spec.md) | Docker image, compose, and configuration |

## Conventions
- Requirements use RFC 2119 keywords (SHALL, SHOULD, MAY).
- Each requirement has at least one `#### Scenario:` in WHEN / THEN form.
- Requirement IDs (`REQ-<AREA>-<n>`) are referenced from [../acceptance-criteria.md](../acceptance-criteria.md) and [../tasks.md](../tasks.md).
