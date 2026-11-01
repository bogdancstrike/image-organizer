# Contributing

Thanks for helping make Auto Image Organizer better! 🌸

## Ways to help
- **Presets**: add a folder set for a niche you know (tattoo studio, dog shows, architecture …) in
  [`backend/app/presets.py`](backend/app/presets.py). Each category is a name, an emoji and 2–4 short *visual* prompts.
- **Bugs**: open an issue with steps, what you expected, and `Settings → System → Copy settings as JSON`.
- **Features**: check [docs/tasks.md](docs/tasks.md) (backlog) and open an issue to discuss first.
- **Docs & translations** are always welcome.

## Workflow
1. Specs first: new behavior gets a requirement + scenario in `docs/openspec/specs/*` and a task in `docs/tasks.md`.
2. Code + tests: `cd backend && pytest -q` (runs in about 2 s with a fake embedder, no network), and `cd frontend && npm run build`.
3. Check it end to end: `docker compose up -d --build`, then sort a sample folder.
4. Conventional commits (`feat:`, `fix:`, `docs:` …), small focused PRs.

## Rules of the house
- Never delete user files. Moves must be journaled and undoable.
- Local first: anything that sends data off the machine must be opt-in and token-frugal.
- Never commit secrets. `.env` is git- and docker-ignored.
