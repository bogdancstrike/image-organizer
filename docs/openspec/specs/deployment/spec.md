# Deployment

## Requirements

### Requirement: REQ-DEP-1 One-command start
`docker compose up -d --build` SHALL build and start the whole app (UI and API) on `http://localhost:8080`
(port configurable with `PORT`).

### Requirement: REQ-DEP-2 Image
The Dockerfile SHALL be multi-stage: a Node stage builds the frontend; the Python 3.12-slim runtime stage installs
ffmpeg and the backend, bundles the CLIP ONNX models (downloaded at build time), copies the built UI, and runs as a non-root
user whose UID/GID can be configured (`PUID`/`PGID`, default 1000), so moved files keep the host user as owner.

### Requirement: REQ-DEP-3 Volumes
The compose file SHALL mount:
- `${LIBRARY_PATH:-./sample-library}` → `/library` (read-write; the folder to organize);
- `./data` → `/data` (cache, thumbnails, journals, custom category sets).

### Requirement: REQ-DEP-4 Configuration
The service SHALL read `.env` if it exists (`required: false`). Variables:
`OPENAI_API_KEY` (optional), `OPENAI_MODEL` (default `gpt-5.6-luna`), `OPENAI_REASONING_EFFORT` (default `low`),
`LIBRARY_PATH`, `PORT`, `PUID`, `PGID`, `WORKERS` (analysis threads), `OUTPUT_DIR_NAME` (default `Organized`).
The key SHALL never reach the browser; the UI only learns whether AI is available.

### Requirement: REQ-DEP-5 Health
`GET /api/health` SHALL return `{status:"ok", ai_available, model, version}`, and compose SHALL define a healthcheck against it.

### Requirement: REQ-DEP-6 Tests in container
`docker compose run --rm organizer pytest -q` SHALL run the backend test suite inside the image.
