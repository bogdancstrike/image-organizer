# Acceptance Criteria

A release is accepted when every item below passes. **How** says how each one is checked:
`unit` = pytest in `backend/tests`, `e2e` = the scripted run in [development.md](development.md#end-to-end-check),
`manual` = by eye in the browser.

| # | Criterion | Specs | How |
|---|---|---|---|
| AC-1 | `docker compose up -d --build` from a clean clone serves the UI on :8080, and `/api/health` reports `ok` | DEP-1,2,5 | e2e |
| AC-2 | Only supported media are found; hidden folders and `Organized/` are skipped; `../` paths are rejected with 400 | SCAN-1..3 | unit |
| AC-3 | Every file gets a thumbnail (photos, HEIC, videos), and corrupt files are reported without aborting | ANL-1,3,7 | unit + e2e |
| AC-4 | A second analysis of an unchanged folder computes 0 embeddings | ANL-6 | unit |
| AC-5 | Byte-identical and resized copies are grouped, the largest copy is kept, and the rest are planned into `_Duplicates` | DUP-1..3 | unit |
| AC-6 | Preset strategy: every file maps to a preset category or `Unsorted`; screenshots go to `Screenshots` | CAT-1,3,4 | unit + e2e |
| AC-7 | A user-defined set produces exactly the user's folders; invalid sets get 422 | CAT-2 | unit |
| AC-8 | Auto strategy works **without** an API key (vocabulary names) and **with** a key (exactly one naming call) | CAT-5,9 | unit + e2e |
| AC-9 | By-date strategy puts files in `YYYY/MM - Month` | CAT-6 | unit |
| AC-10 | Until Apply, the library is unchanged | ORG-1 | unit + e2e |
| AC-11 | Apply moves files, resolves collisions, and writes a journal; Undo restores every path and removes the empty folders it created | ORG-3..5 | unit + e2e |
| AC-12 | The SSE stream replays past events to late subscribers | ORG-2 | unit |
| AC-13 | The UI shows the pile → flight → card animation, the counters count up, and the flower appears at the end | UI-1,2 | manual |
| AC-14 | Settings, category editor, history and undo work from the UI | UI-3..5 | manual |
| AC-15 | An OpenAI failure (bad key or timeout) degrades to local behavior with a visible warning | CAT-9 | unit |
| AC-16 | The API key never appears in any API response or in the frontend bundle | DEP-4 | unit + e2e (`grep`) |
