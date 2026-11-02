# Search tags, badge explanations and Social Media implementation plan

> **For agentic workers:** Execute inline using the executing-plans workflow; the user has authorized implementation and commits on main. Keep each subsystem independently testable.

**Goal:** Explain photo badges, make local automatic tags searchable, and recommend photos for social-media review.

**Architecture:** Shared accessible badge tooltips explain existing photo metadata. A versioned local tagger reuses image embeddings and stores multi-label results in each model's SQLite cache. Library search combines semantic similarity, tags, and OCR; exact tag facets narrow the folder scope. A social scoring overlay uses measured image signals and paired semantic cues alongside existing genre-aware culling, exposed through a Social Media preset/recipe and Cull controls.

**Tech Stack:** Python/FastAPI, NumPy, CLIP/SigLIP 2, SQLite; React/TypeScript/Ant Design; pytest/Vitest/Playwright.

## 1. Badge explanations

- [x] Create `frontend/src/components/PhotoBadge.tsx`: `InfoBadge({message, children, className})` uses Ant Design Tooltip with hover/focus triggers and an accessible name. Centralize source/quality descriptions.
- [x] Update `FilesDrawer.tsx`, `ReviewTab.tsx`, `CategoryCard.tsx` and `MediaViewer.tsx`. Image-detail hover must not cover badge-specific hover. Explain AI, video, smile, flags, sidecars, face counts, Picks and burst icons.
- [x] Verify hover/focus messages and that photo clicks still open the viewer; run component tests and commit to main.

## 2. Local automatic tags and search

- [x] Create `backend/app/tagging.py`: `tag_images(cache, ordered, embedder)` returns `{file_id: [{label, score, group, source}]}`. Use independent positive/reference prompts, evidence thresholds, group limits and a total cap; do not force labels onto ambiguous images. Metadata supplies orientation and screenshot labels. Version/cache entries by path, size, mtime and model.
- [x] Integrate default-on `options.auto_tags` into `main.py`/`jobs.py`; include tags in plans. Tagging failures warn without preventing a usable sort. Disabled tagging preserves existing cache.
- [x] Extend `library.py` and endpoints with scoped tag facets and repeated `tag` filters (AND semantics); expose tag metadata on search/similar results and boost whole-token/alias matches. Ignore missing or stale tag entries.
- [x] Update API types, Library controls/results/viewer and photo details. Allow existing folders to refresh tags without Apply. Reject failed indexing jobs instead of reporting success.
- [x] Test multi-label evidence, abstention, cache invalidation, aliases, exact filters, folder boundaries, stale files, and frontend filtering/tag visibility.

## 3. Social Media selection

- [x] Document primary research: image popularity/content versus social context, LaMem memorability, NIMA and CLIP-IQA. Distinguish measured heuristics from trained predictors.
- [x] Create `backend/app/social.py`: `assess(quality, E, embedder, format)` returns small-screen clarity, crop retention, contrast/color and semantic impact signals. Assess crop retention from face boxes and edge energy; never crop or publish automatically.
- [x] Extend quality cache version for image dimensions, contrast, restrained colorfulness and thumbnail clarity. Blend optional social score into absolute recommendations before shoot/scene ranking; preserve technical rejects, rating thresholds and diversity.
- [x] Add `social_media`, `social_format` and `social_weight` options, plus Social Media preset/recipe. Selecting it must use the same culling engine as explicit social Cull mode.
- [x] Add Quick settings social controls, format choices and component explanations; preserve active recipe consistency.
- [x] Test crop loss, noise/clipping, neutral fallbacks, social overlay influence, preset routing and user interactions.

## 4. Verification and delivery

- [x] Run backend and frontend suites with separate >=90% coverage gates; build UI and inspect real local model output on read-only samples.
- [x] Browser-check tooltips, tags/search, Social Media preset and Cull controls; rebuild local app.
- [x] Update README/API/configuration/research/tasks with exact behavior and limitations. Commit/push main and verify CI.

## Extended user requirements

- Mapped 30 core ideas from the supplied 50-idea article to code/tests in `docs/culling-algorithms.md`; scoped approximations and unbundled trained models are identified separately.
- Added public-workflow adaptations from Aftershoot: 2–4-photo survey comparison, synchronized native-size zoom/pan, face crops and destination overrides.
- Added collapsible settings categories and compact folder ordering.
- Checkpoint `1c1c19f` pushed to main and deployed locally. Before final tag-gate tuning: backend 157 tests/90.85%; frontend 82 tests/93.22% lines and 90.77% statements.
- [x] Finish real-model tagging validation and desktop/mobile browser checks; local backend 158 tests/90.87%, frontend 83 tests/93.24% lines and 90.78% statements.
- [x] Verify collapsed settings, Auto strategy, AI/tag hover messages, folder ordering, 200% synchronized comparison with face crops, exact tag search, and 390px mobile layout.
- [x] Checkpoint CI passed: https://github.com/bogdancstrike/image-organizer/actions/runs/41493976964
- [ ] Push and redeploy final tag/tooltip refinements; verify final CI.
