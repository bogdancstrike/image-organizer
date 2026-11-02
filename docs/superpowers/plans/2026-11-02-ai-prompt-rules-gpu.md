# AI prompt rules and optional GPU implementation plan

> **For agentic workers:** Implement this plan task by task, with verified commits at each checkpoint. Execution stays in this session on `main`, committing and pushing verified checkpoints as requested.

**Goal:** Sort media with natural-language AI routing instructions, offer opt-in NVIDIA GPU inference through `.env`, and reconcile documented feature status with tested implementations.

**Architecture:** Add a `rules` strategy to the existing plan/review/apply/undo pipeline. AI compiles instructions into validated relative destinations, then classifies thumbnails into rule IDs; unmatched files use an explicit catch-all or Unsorted. Reject malformed model output and unsafe paths, and fail the rule job visibly if AI is unavailable. Local recognition chooses explicit CPU or CUDA execution providers; Compose extends a device-specific runtime configuration using `DEVICE=cpu|gpu`.

**Tech Stack:** FastAPI/Pydantic, OpenAI Responses API, FastEmbed/ONNX Runtime, React/TypeScript/antd, Docker Compose, pytest.

## Task 1: AI rules backend

Files: `backend/app/rules.py`, `backend/app/llm.py`, `backend/app/jobs.py`, `backend/app/main.py`, `backend/tests/test_rules.py`.

- [x] Add tests for dated nested destinations, unsafe paths, invalid AI results, unavailable AI, catch-all routing, and apply/undo containment.
- [x] Replace the orphan local parser prototype with a focused validated rule model. Preserve `{date}`, `{today}`, `{year}`, `{month}`, `{iso}` expansion. Reject absolute paths, empty segments, traversal, Windows drive paths, control characters, oversized names, duplicate destinations, and multiple catch-alls.
- [x] Add structured AI methods: `compile_rules(prompt, today)` and `classify_rules(thumbs, rules)`. Validate every rule/label and exact response cardinality. Keep rule IDs separate from destination strings.
- [x] Add `rules` and `rules_prompt` to the request schema. Validate a non-empty prompt and require configured AI for this strategy. Compile before scan, use all eligible thumbnails in batches, keep duplicate/quality handling, and set explicit category paths so rules preserve their requested nesting.
- [x] Verify with `pytest -q tests/test_rules.py tests/test_api.py tests/test_core.py`; commit and push the checkpoint.

## Task 2: User-facing rules mode

Files: `frontend/src/api.ts`, `frontend/src/settings.ts`, `frontend/src/App.tsx`, `frontend/src/components/SettingsDrawer.tsx`, `frontend/src/components/HistoryTab.tsx`, `frontend/src/i18n.tsx`, `frontend/src/i18n-more.ts`.

- [x] Add `rules` strategy and persisted `rulesPrompt` value; send `rules_prompt` to the backend.
- [x] Add Prompt rules to organizing controls, a labelled instructions textarea with landscape/date example, key-availability guidance, and clear photo-sharing explanation. Hide irrelevant preset/auto controls for this mode.
- [x] Display AI rules status in Sort and History; preserve existing Apply/Undo controls.
- [x] Build with `npm run build`; exercise a mocked AI rule flow in Playwright, including reload, disabled state without a key, and review destinations. Commit and push.

## Task 3: Opt-in GPU

Files: `backend/app/config.py`, `backend/app/embedder.py`, `backend/app/main.py`, `backend/tests/test_device.py`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `docker/compose.cpu.yml`, `docker/compose.gpu.yml`.

- [x] Test CPU default, invalid devices, CUDA absence, provider propagation to both embedding towers, separate singleton identity, and GPU initialization failure.
- [x] Read `DEVICE=cpu|gpu`; explicitly select CPU providers in CPU mode and CUDA providers in GPU mode. Verify CUDA is actually selected by initialized sessions; fail clearly instead of silently falling back.
- [x] Report selected device in health. Keep analysis cache reusable across devices.
- [x] Add a GPU Docker target with GPU runtime dependencies and CUDA/cuDNN libraries while retaining the CPU default target. Use an interpolated Compose `extends` file so changing DEVICE in .env selects the correct build target and GPU reservation without an extra launch command.
- [x] Verify CPU/GPU Compose rendering and tests. Check available hardware before attempting GPU inference; document any unavailable hardware validation. Commit and push.

## Task 4: Existing features, docs, final verification

Files: `backend/tests/test_people_ocr.py`, `backend/tests/test_pro.py`, `backend/tests/test_picks.py`, `README.md`, `docs/tasks.md`, `docs/configuration.md`, `docs/api.md`, `docs/categories.md`, `docs/development.md`.

- [x] Run existing OCR, XMP apply/undo, Picks, expression/group-shot tests; inspect SigLIP model wiring and model-specific cache tests. Repair concrete failures with regression coverage.
- [x] Add missing meaningful coverage for model cache separation and end-to-end Picks metadata if inspection shows gaps.
- [x] Mark implemented OCR/XMP/SigLIP/Picks/expression work complete. Keep partial translation and genuinely missing features open.
- [x] Document AI prompt rules, failure behavior, date paths, image sharing, GPU setup, CPU default, GPU scope, and exact launch commands.
- [x] Run the complete backend suite, frontend build, Compose checks, and browser smoke checks. Review diffs, update plan checkboxes, commit and push. Fast-forward main after all checks pass.

## Coverage requirement (added during implementation)

- [x] Enforce at least 90% line coverage independently across all backend application modules and all frontend TypeScript/TSX source. Do not omit product modules from measurement.
- [x] Add pytest-cov and Vitest/Testing Library with V8 reports, including failure-path and interaction coverage.
- [x] Add CI checks for both coverage thresholds and document local commands. Hardware and paid API smoke tests supplement deterministic tests.

## Culling expansion (requested during implementation)

- [x] Record portrait, fashion/modeling, landscape and aesthetic-assessment research in `docs/culling-research.md`, distinguishing published evidence from application heuristics.
- [x] Add deterministic ranking regressions for dark artistic photos, clipped highlights, main/group faces, profile-sensitive expression, minimum pick quality, scene diversity and star/export consistency.
- [x] Add `pick_profile` (`auto`, `portrait`, `fashion`, `landscape`, `general`). Infer genre locally in auto mode. Blend technical quality, expression, composition, lighting and genre presentation with profile-specific weights; retain absolute quality alongside within-shoot/scene comparisons.
- [x] Rank all cull photos, even when Picks is off. Use the recommendation score for keeper thresholds, displayed stars and XMP ratings. Keep enabled rejection checks authoritative and never fill pick quotas with unusable/redundant frames.
- [x] Show profile, score, component values and reasons in the viewer; add recommendation sorting/filtering in Review. Verify in the backend suite, frontend interaction tests and a real sample cull.

## Verified checkpoints

- Backend: 132 tests passing; 90.42% line coverage without models (CI-like environment). Earlier bundled-model run: 90.64%.
- Frontend: 67 tests passing; 92.80% lines and 90.51% statements across all TypeScript/TSX source.
- GPU: actual CLIP (512 dimensions) and SigLIP 2 (768 dimensions) image/text inference on NVIDIA RTX 3080.
- Live AI: three-sample prompt-rule plan, two API calls, expected landscape/other routing, no source moves.
- Real cull/OCR/XMP: seven samples, portrait and landscape picks, invoice text read, seven copied sidecars, successful Undo.
- Compose: CPU has no GPU reservation; GPU target reserves one NVIDIA device. CPU stays the default Docker target.
