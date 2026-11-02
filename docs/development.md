# Development

## Layout
```
backend/            FastAPI app (app/) + pytest suite (tests/)
frontend/           React 19 + Vite + antd 6 + Tailwind 4 + shadcn/ui-style components
  src/anim/         canvas animation engine
  src/components/   UI (ui/ = shadcn primitives)
  src/theme.tsx     themes (Graphite / Light / Lavender) + antd theme configs
docker/             container entrypoint
scripts/            sample-data downloaders
docs/               specs (OpenSpec), plan, tasks, guides
```

## Everything in Docker (recommended)
```bash
docker compose up -d --build                    # app on :8080
docker compose run --rm organizer pytest -q     # backend tests inside the image
docker compose logs -f
```

## Local dev loop (hot reload)
```bash
# backend (Python 3.12, ffmpeg installed)
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
LIBRARY_ROOT=$HOME DATA_DIR=../data uvicorn --factory app.main:create_app --reload --port 8000

# frontend (Node 22+): proxies /api to :8000
cd frontend && npm install && npm run dev       # http://localhost:5173
```

## Tests and coverage

Both suites enforce at least **90% line coverage** across application source. Frontend statements also have a
90% threshold. Branch/function coverage is reported separately. Product modules are not excluded from measurement.

```bash
# Backend: Python 3.12 + ffmpeg; install test dependencies once
cd backend
pip install -r requirements-dev.txt
pytest -q --cov=app --cov-report=term-missing --cov-report=html --cov-report=json:coverage/coverage.json
# HTML: backend/coverage/html/index.html

# Frontend: Node 22.12+ (22 LTS) or a supported newer LTS
cd frontend
npm ci
npm run test:coverage
npm run build
# HTML: frontend/coverage/index.html; summary: frontend/coverage/coverage-summary.json
```

The deterministic suites mock paid APIs and model results at their boundaries. They cover plan/apply/undo,
path validation, OCR, ratings/labels, model/device selection, culling recommendations, UI interaction, navigation,
settings, library search and the animation engine. No API key or GPU is required to run them. Real inference and
small live AI smoke checks supplement the tests during development.

[CI](../.github/workflows/tests.yml) runs each coverage gate and uploads separate backend/frontend reports.
Changing `DEVICE` does not change the CPU test suite; GPU inference requires the optional runtime described in
[configuration.md](configuration.md#cpu-or-nvidia-gpu).

## End-to-end check
```bash
./scripts/download-samples.sh && python3 scripts/download-portraits.py
docker compose up -d --build
# in the UI: choose sample-library/Downloads → Sort → Apply → Undo
# or by API:
curl -s -XPOST localhost:8080/api/jobs -H 'Content-Type: application/json' \
  -d '{"source":"<path under LIBRARY_PATH>/sample-library/Portraits","strategy":"preset","set_id":"people-style"}'
```
Acceptance criteria are in [acceptance-criteria.md](acceptance-criteria.md).

## Conventions
- Specs first: new behavior gets a requirement + scenario in `docs/openspec/specs/*` and a task in `docs/tasks.md`.
- Conventional commits (`feat:`, `fix:`, `docs:` …).
- Never write secrets to the repo; `.env` is git- and docker-ignored.
