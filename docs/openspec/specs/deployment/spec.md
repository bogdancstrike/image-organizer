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
`OPENAI_API_KEY` (optional), `OPENAI_MODEL` (default `gpt-6-luna`), `OPENAI_REASONING_EFFORT` (default `low`),
`LIBRARY_PATH`, `PORT`, `PUID`, `PGID`, `WORKERS` (analysis threads), `OUTPUT_DIR_NAME` (default `Organized`).
The key SHALL never reach the browser; the UI only learns whether AI is available.

### Requirement: REQ-DEP-5 Health
`GET /api/health` SHALL return `{status:"ok", ai_available, model, version}`, and compose SHALL define a healthcheck against it.

### Requirement: REQ-DEP-6 Tests in container
`docker compose run --rm organizer pytest -q` SHALL run the backend test suite inside the image.


### Requirement: REQ-DEP-7 Optional GPU
`DEVICE` SHALL default to `cpu`; `gpu` SHALL select a CUDA image and reserve one NVIDIA GPU through the same
Compose command. Both CLIP and SigLIP 2 text/image towers SHALL use explicit providers. CPU mode SHALL not
select GPUs automatically. Missing/failed CUDA SHALL produce a clear error rather than silent CPU fallback.
Health SHALL report the configured device; analysis cache SHALL remain reusable across devices.

### Requirement: REQ-DEP-8 Coverage gates
CI SHALL enforce at least 90% line coverage separately for backend and frontend application source and publish
separate coverage reports. Frontend statement coverage SHALL also reach 90%. Paid API and GPU calls SHALL be
mocked at their boundaries in deterministic tests; optional real smoke checks supplement those tests.
