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

- [ ] Update `frontend/src/components/MediaViewer.tsx`: desktop grid with image left and a persistent scrollable scoring panel right. Show recommendation rating, profile, component scores, reasons, quality flags, face summaries, tags and attached files.
- [ ] Keep Ant Design zoom, rotation, keyboard navigation and close controls working. Stack the panel on narrow screens.
- [ ] Add viewer interaction tests and browser checks; retain >=90% frontend lines/statements and a passing build.

## Phase 4: Verification and delivery

- [ ] Update architecture/development documentation, import-path references and culling method links.
- [ ] Verify real CPU/GPU container startup and read-only sample workflows; preserve cached data and HTTP behavior.
- [ ] Commit/push main, redeploy the app, check health and final CI. Stop temporary QA containers.

## Existing checkpoint

- `f0b42d4` pushed and deployed; local app healthy. Final CI run: https://github.com/bogdancstrike/image-organizer/actions/runs/41499984565 (check completion).
- Before refactor: backend 158 tests / 90.87%; frontend 83 tests / 93.24% lines / 90.78% statements.
- Temporary `image-organizer-feature-qa` on port 18080 mounts backend/dist live and seven sample images read-only. Stop it before moving modules; production container uses an immutable image and stays available.

## Additional requirements received during implementation

- [ ] Improve the remaining person assignments in `/home/bogdan/Downloads/Boudoir-10-selected-items`: latest user reports four correct identities plus 162 images in Other people, all belonging to those identities. Combine reliable face anchors with multiple appearance/body/detail prototypes and sequence context; retain ambiguity when evidence conflicts. Validate read-only against the actual folder, comparing missed and incorrect assignments rather than forcing everything into known people.
- [ ] Add decision provenance to full-screen review, including trashed photos: category/score/threshold reason, technical flags, duplicate basis and keeper path, recoverable-trash action, rule/model match, and manual override history. Applied/trashed preview paths must remain usable and Undo must restore them.
- [ ] Preserve periodic tested commits/pushes on main and redeployments while these requirements are implemented.

## Refactor checkpoint

- 173 backend tests passed; 91.19% coverage.
- OpenAPI compared before/after: 35 paths, identical request/response schemas and operations except added documentation tags.
- Root entry point is 65 lines; numerical/domain dependencies, model adapters and SQLite stores are separated.
- Guard tests enforce dependency direction and factory isolation.
