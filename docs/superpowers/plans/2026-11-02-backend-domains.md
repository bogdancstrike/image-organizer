# Backend domain packages and full-screen review implementation plan

> **For agentic workers:** Execute inline using the executing-plans workflow. User explicitly authorizes main commits/pushes and redeployments. Preserve the untracked `.idea/` directory.

**Goal:** Give the backend cohesive domain packages and clear dependency boundaries, and present full-screen photos beside their recommendation details.

**Architecture:** Keep `app.main:create_app` as the stable composition entry point. Separate API adapters, numerical/domain logic, application orchestration, and model/storage adapters. Prefer explicit imports and small injected ports over compatibility shims or generic frameworks.

**Tech Stack:** Existing FastAPI/Pydantic, Python/NumPy/ONNX/SQLite, React/Ant Design and current tests.

## Package map

- `app/api`: request schemas, runtime context, domain-specific route factories.
- `app/catalog`: validated category definitions and built-in presets; storage moves to infrastructure.
- `app/media`: decoding/scanning and media metadata.
- `app/recognition`: classification, people clustering, tags, prompt rules and embedding ports.
- `app/culling`: quality signals, ranking, social signals, duplicates and culling decision service.
- `app/organization`: job orchestration, destinations and journaled file operations.
- `app/library`: indexed search, tagging facets and geography/trips.
- `app/infrastructure`: runtime settings, model providers, cache/database/category storage and optional OpenAI adapter.

## Phase 1: Packages and imports

- [x] Move existing modules into the package map with real `__init__.py` files; keep only the entry point/version at the root.
- [x] Update relative/absolute imports structurally, including tests, Docker references and documentation. Never replace `app.db` database filenames as Python module paths.
- [x] Extract the embedding protocol/normalization into recognition ports; numerical classification depends on this interface.
- [x] Separate catalog validation/preset helpers from its SQLite store.
- [x] Run the complete backend suite and >=90% coverage gate. Commit/push a tested checkpoint.

## Phase 2: Responsibility boundaries

- [x] Extract Cull decisions from JobManager into `app/culling/service.py`, returning assignments/categories/recommendation metadata without HTTP/storage dependencies.
- [x] Keep model-loading face/identity adapters outside scoring/identity clustering logic; update tests and inject existing interfaces.
- [x] Move SQLite read operations behind cache methods so library search does not reach into a private database connection.
- [x] Split API schemas and routers into cohesive modules. A typed runtime context supplies services; main wires them and mounts the SPA last. Preserve routes, status codes, payloads and factory isolation.
- [x] Add meaningful architecture tests for prohibited dependency directions and HTTP route contracts; rerun all backend tests/coverage.

## Phase 3: Full-screen photo review

- [x] Update `frontend/src/components/MediaViewer.tsx`: desktop grid with image left and a persistent scrollable scoring panel right. Show recommendation rating, profile, component scores, reasons, quality flags, face summaries, tags and attached files.
- [x] Keep Ant Design zoom, rotation, keyboard navigation and close controls working. Stack the panel on narrow screens.
- [x] Add viewer interaction tests and browser checks; retain >=90% frontend lines/statements and a passing build.

## Phase 4: Verification and delivery

- [x] Update architecture/development documentation, import-path references and culling method links.
- [x] Verify real CPU/GPU container startup and read-only sample workflows; preserve cached data and HTTP behavior.
- [ ] Commit/push main, redeploy the app, check health and final CI. Stop temporary QA containers.

## Existing checkpoint

- `f0b42d4` pushed and deployed; local app healthy. Final CI run: https://github.com/bogdancstrike/image-organizer/actions/runs/41499984565 (check completion).
- Before refactor: backend 158 tests / 90.87%; frontend 83 tests / 93.24% lines / 90.78% statements.
- Temporary `image-organizer-feature-qa` on port 18080 mounts backend/dist live and seven sample images read-only. Stop it before moving modules; production container uses an immutable image and stays available.

## Additional requirements received during implementation

- [x] Improve the remaining person assignments in `/home/bogdan/Downloads/Boudoir-10-selected-items`: latest user reports four correct identities plus 162 images in Other people, all belonging to those identities. Combine reliable face anchors with multiple appearance/body/detail prototypes and sequence context; retain ambiguity when evidence conflicts. Validate read-only against the actual folder, comparing missed and incorrect assignments rather than forcing everything into known people.
- [x] Add decision provenance to full-screen review, including trashed photos: category/score/threshold reason, technical flags, duplicate basis and keeper path, recoverable-trash action, rule/model match, and manual override history. Applied/trashed preview paths must remain usable and Undo must restore them.
- [x] Preserve periodic tested commits/pushes on main and redeployments while these requirements are implemented.

## Refactor checkpoint

- 173 backend tests passed; 91.19% coverage.
- OpenAPI compared before/after: 35 paths, identical request/response schemas and operations except added documentation tags.
- Root entry point is 65 lines; numerical/domain dependencies, model adapters and SQLite stores are separated.
- Guard tests enforce dependency direction and factory isolation.

## Further requirements received

- [x] Library relevance bug: remove forced minimum-12 results and gate compound concepts. Initial local fix passes 177 BE tests / 91.24%; actual read-only SigLIP query `dog in a snow` returns 0 from the 1,029-photo folder, while portrait returns 15. Add deployment/browser verification.
- [x] Winner photo: exactly one highlighted recommendation per Cull, retaining its ordinary folder assignment; best-available warning if all candidates have issues.
- [x] Research and integrate a licensed CPU-friendly trained aesthetic-preference signal for Social Media; verify exact embedding-space compatibility, model provenance and inference rather than treating semantic prompts as a trained popularity model.
- [x] Full-screen two-column viewer is implemented and builds, with a persistent score/reason panel; fix synthetic arrow-key test (Ant Design reads keyCode), finish provenance integration and deploy.

## Viewer, search and Winner checkpoint

- Backend: 179 passing tests; 91.25% coverage. Frontend: 88 passing tests; 93.34% lines and 90.78% statements; production build passes.
- Chromium verifies Winner entry, desktop image/details columns, score bars, next-photo keyboard navigation, Escape, mobile stacked layout and no page errors.
- Fixed preview opening during list updates and made dark preview controls visible.
- Actual read-only library validation: `dog in a snow` returns zero results in 1,029 photos; `portrait` returns relevant results. No minimum result padding.
- Decision provenance and stronger people matching remain in progress.

## Joined viewer and appearance checkpoint

- Score panel now touches the actual image, matches its height on desktop, has square shared corners and rounded outer corners. Browser geometry and desktop/mobile checks pass.
- Replaced single appearance centroids/gender gating with a balanced CPU classifier, multi-view neighbour consensus and two-sided camera-sequence support. Includes unmatched partial faces; reliable face assignments are preserved.
- Same 1,029-photo folder, same options, read-only: Other people 162 → 41; 136/162 previously unknown views recovered; 15 previously appearance-assigned views now abstain. All face-based assignments preserved.
- Five-fold validation of 476 face-confirmed full-image references: 445 accepted, 438 agreeing with withheld face labels (98.43%); 31 abstained. This measures appearance agreement on face-confirmed views, not accuracy on unseen body/detail shots or a professional benchmark.
- Backend 183 tests / 91.34%; frontend 88 tests / 93.34% lines / 90.78% statements.

## LAION and decision provenance verification

- Original MIT-licensed LAION B/32 head converted to safe JSON with weights-only PyTorch loading; production inference uses NumPy and verifies the packaged checksum. Exact encoder-space guards reject SigLIP and wrong-dimensional vectors. Golden result matches the original linear head.
- Social Media exposes a named LAION setting, a separate learned score and a 30% contribution inside the user-controlled social blend. All viable nonduplicates are scored when CLIP vectors already exist; other encoders use a bounded 256-photo shortlist with a visible limit notice. Model failures retain ordinary scores with a warning.
- Seven real sample images: CPU CLIP, CPU SigLIP+CLIP and GPU CLIP all complete without warnings; displayed learned scores match CPU/GPU. Network-disabled CPU inference succeeds without PyTorch installed.
- Real 1,029-photo read-only culling run completes with no file errors, 55 duplicates, one Winner and the expected shortlist notice.
- Backend 210 tests / 91.61%; desktop/mobile browser checks pass with learned components and observable decision evidence. Frontend verification refreshed after removing the generic quality-assignment sentence at user request.
- Specific decision evidence covers duplicate measurements/policy/keeper, thresholds, flags, identity-match evidence and manual override history. Applied/trashed previews recover from journals on restart and Undo restores the original paths.

- Final local checks: 210 backend tests / 91.61%; 89 frontend tests / 93.34% lines and 90.74% statements; production build and desktop/mobile browser checks pass. Large-folder rerun scores exactly 256 nonduplicates, produces one Winner and includes evidence on every plan item.
- New follow-up: improve kitchen/background-scene search recall on the real folder while preserving absent-concept precision.

## Complete learned assessment checkpoint

- Removed the 256-photo cap at user request. Every nonduplicate photo with available analysis receives LAION assessment, including photos carrying technical warnings. CLIP reuses vectors; other encoders compute/cache their own CLIP vectors in batches.
- Real 1,029-photo SigLIP run: 974/974 nonduplicates scored; 55 duplicates; zero warnings or file errors. Backend 213 tests / 91.67%; frontend 89 tests / 93.34% lines and 90.74% statements. Production build passes.
- Fixed the accessibility-test label following the explicit LAION naming update; the previous CI failure was this stale test label.
- Pending user regressions: trace preferred photos and improve Winner/Picks/Keepers and false blur; recover missed face in DSCF1773; remove duplicate-to-trash policy/UI, preserve legacy Undo; wardrobe classification for DSC05803 sportswear.

## Duplicate trash removal checkpoint

- Removed the duplicate-trash UI option, API policy and always-on misleading card suffix/icon. Old saved UI choices and incoming legacy requests normalize to a Duplicates folder. Unapplied legacy plans migrate before Apply; applied legacy runs keep their journals, previews and Undo.
- Backend tests cover both legacy plan migration and historical trash-preview restoration. Current implementation never sends new duplicate plans to trash.
