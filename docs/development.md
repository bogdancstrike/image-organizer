# Development

## Layout
```
backend/            FastAPI app (app/) + pytest suite (tests/)
frontend/           React 19 + Vite + antd 6 + Tailwind 4 + shadcn/ui-style components
  src/anim/         canvas animation engine
  src/components/   UI (ui/ = shadcn primitives)
  src/theme.tsx     themes (pink / blue / dark) + antd theme configs
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
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
LIBRARY_ROOT=$HOME DATA_DIR=../data uvicorn --factory app.main:create_app --reload --port 8000

# frontend (Node 22+): proxies /api to :8000
cd frontend && npm install && npm run dev       # http://localhost:5173
```

## Tests
- Backend: `cd backend && pytest -q`. A deterministic `FakeEmbedder` stands in for CLIP and a fake OpenAI client
  for Luna, so the suite runs in about 2 s with no network.
- Frontend: `npm run build` type-checks (`tsc -b`) and builds.

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
