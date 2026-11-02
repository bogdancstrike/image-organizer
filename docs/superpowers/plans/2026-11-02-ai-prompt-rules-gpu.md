# AI prompt rules and optional GPU implementation plan

> **For agentic workers:** Implement this plan task by task, with verified commits at each checkpoint. Execution stays in this session on `feat/ai-prompt-rules-gpu`.

**Goal:** Sort media with natural-language AI routing instructions, offer opt-in NVIDIA GPU inference through `.env`, and reconcile documented feature status with tested implementations.

**Architecture:** Add a `rules` strategy to the existing plan/review/apply/undo pipeline. AI compiles instructions into validated relative destinations, then classifies thumbnails into rule IDs; unmatched files use an explicit catch-all or Unsorted. Reject malformed model output and unsafe paths, and fail the rule job visibly if AI is unavailable. Local recognition chooses explicit CPU or CUDA execution providers; Compose selects an optional GPU image and device reservation using `DEVICE=cpu|gpu`.

**Tech Stack:** FastAPI/Pydantic, OpenAI Responses API, FastEmbed/ONNX Runtime, React/TypeScript/antd, Docker Compose, pytest.

## Task 1: AI rules backend

Files: `backend/app/rules.py`, `backend/app/llm.py`, `backend/app/jobs.py`, `backend/app/main.py`, `backend/tests/test_rules.py`.

- [ ] Add tests for dated nested destinations, unsafe paths, invalid AI results, unavailable AI, catch-all routing, and apply/undo containment.
- [ ] Replace the orphan local parser prototype with a focused validated rule model. Preserve `{date}`, `{today}`, `{year}`, `{month}`, `{iso}` expansion. Reject absolute paths, empty segments, traversal, Windows drive paths, control characters, oversized names, duplicate destinations, and multiple catch-alls.
- [ ] Add structured AI methods: `compile_rules(prompt, today)` and `classify_rules(thumbs, rules)`. Validate every rule/label and exact response cardinality. Keep rule IDs separate from destination strings.
- [ ] Add `rules` and `rules_prompt` to the request schema. Validate a non-empty prompt and require configured AI for this strategy. Compile before scan, use all eligible thumbnails in batches, keep duplicate/quality handling, and set explicit category paths so rules preserve their requested nesting.
- [ ] Verify with `pytest -q tests/test_rules.py tests/test_api.py tests/test_core.py`; commit and push the checkpoint.

## Task 2: User-facing rules mode

Files: `frontend/src/api.ts`, `frontend/src/settings.ts`, `frontend/src/App.tsx`, `frontend/src/components/SettingsDrawer.tsx`, `frontend/src/components/HistoryTab.tsx`, `frontend/src/i18n.tsx`, `frontend/src/i18n-more.ts`.

- [ ] Add `rules` strategy and persisted `rulesPrompt` value; send `rules_prompt` to the backend.
- [ ] Add Prompt rules to organizing controls, a labelled instructions textarea with landscape/date example, key-availability guidance, and clear photo-sharing explanation. Hide irrelevant preset/auto controls for this mode.
- [ ] Display AI rules status in Sort and History; preserve existing Apply/Undo controls.
- [ ] Build with `npm run build`; exercise a mocked AI rule flow in Playwright, including reload, disabled state without a key, and review destinations. Commit and push.

## Task 3: Opt-in GPU

Files: `backend/app/config.py`, `backend/app/embedder.py`, `backend/app/main.py`, `backend/tests/test_device.py`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `scripts/start.sh`.

- [ ] Test CPU default, invalid devices, CUDA absence, provider propagation to both embedding towers, separate singleton identity, and GPU initialization failure.
- [ ] Read `DEVICE=cpu|gpu`; explicitly select CPU providers in CPU mode and CUDA providers in GPU mode. Verify CUDA is actually selected by initialized sessions; fail clearly instead of silently falling back.
- [ ] Report selected device in health. Keep analysis cache reusable across devices.
- [ ] Add a GPU Docker target with GPU runtime dependencies and CUDA/cuDNN libraries while retaining the CPU default target. Add an opt-in Compose service profile sharing the existing configuration and a launcher selecting the correct service from `.env` without requiring manual YAML edits.
- [ ] Verify CPU/GPU Compose rendering and tests. Check available hardware before attempting GPU inference; document any unavailable hardware validation. Commit and push.

## Task 4: Existing features, docs, final verification

Files: `backend/tests/test_people_ocr.py`, `backend/tests/test_pro.py`, `backend/tests/test_picks.py`, `README.md`, `docs/tasks.md`, `docs/configuration.md`, `docs/api.md`, `docs/categories.md`, `docs/development.md`.

- [ ] Run existing OCR, XMP apply/undo, Picks, expression/group-shot tests; inspect SigLIP model wiring and model-specific cache tests. Repair concrete failures with regression coverage.
- [ ] Add missing meaningful coverage for model cache separation and end-to-end Picks metadata if inspection shows gaps.
- [ ] Mark implemented OCR/XMP/SigLIP/Picks/expression work complete. Keep partial translation and genuinely missing features open.
- [ ] Document AI prompt rules, failure behavior, date paths, image sharing, GPU setup, CPU default, GPU scope, and exact launch commands.
- [ ] Run the complete backend suite, frontend build, Compose checks, and browser smoke checks. Review diffs, update plan checkboxes, commit and push. Fast-forward main after all checks pass.
