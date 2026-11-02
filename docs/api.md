# API reference

Base URL: `http://localhost:8080`. Interactive docs: **`/docs`** (Swagger UI) and `/redoc`.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/api/health` | | `{status, version, device, ai_available, model, library_ok, library_name, library_host_path, output_dir, …}` |
| GET | `/api/folders` | `?path=rel/path` | `{path, name, media_count, folders:[{name, path, media_count, has_children}]}` |
| GET | `/api/presets` | | `[CategorySet]` |
| GET | `/api/category-sets` | | custom `[CategorySet]` |
| POST | `/api/category-sets` | `{name, description?, categories:[{name, emoji?, prompts?}]}` | `201 CategorySet` (`422` on duplicate names) |
| PUT / DELETE | `/api/category-sets/{id}` | same / – | `CategorySet` / `204` |
| POST | `/api/jobs` | `JobRequest` | `201 {id}` · `409` if a sort is running · `400` bad folder or AI unavailable for rules · `404` unknown set |
| GET | `/api/jobs/{id}` | `?plan=false` to omit the plan | `JobSnapshot` |
| GET | `/api/jobs/{id}/events` | | `text/event-stream`: each `data:` is a JSON **array** of events; ends with `event: end` |
| POST | `/api/jobs/{id}/cancel` | | `{cancelled}` |
| POST | `/api/jobs/{id}/apply` | `{mode: "move"|"copy"}` | `{run_id, moved, failed, skipped, …}` · `409` if already applied |
| GET | `/api/runs` | | history, newest first |
| POST | `/api/runs/{run_id}/undo` | | `{run_id, status, undo:{restored, problems}}` |
| GET | `/api/thumbs/{sha256}` | | WebP thumbnail (cached forever) |

```jsonc
// JobRequest
{
  "source": "Downloads",          // folder relative to the library root ("" = root)
  "strategy": "preset",           // preset | custom | auto | date | cull | people | trips | places | rules
  "set_id": "people-style",       // preset or custom set id (preset/custom only)
  "options": {
    "output_dir": "Organized",    // "" = directly in the folder; omit = server default
    "recursive": true, "split_media": true,
    "min_confidence": 0.3, "near_duplicates": true, "ai_assist": false,
    "max_clusters": 12, "date_granularity": "month"
  }
}
```

### Events
| type | payload |
|---|---|
| `phase` | `phase`: rules (AI instructions) · scanning · analyzing · checking · reading · faces · deduplicating · categorizing · ai |
| `scanned` | `total, photos, videos, source, source_name` |
| `file` | `id, kind, rel_path, name, thumb` |
| `file_error` | `id, rel_path, error` |
| `progress` | `analyzed, total` |
| `stats` | counters |
| `categories` | `[{id, name, emoji, photos, videos}]` |
| `assign` | `id, category_id, kind` |
| `warning` | `message` |
| `done` / `cancelled` / `error` | summary / – / `message` |

### curl example
```bash
JOB=$(curl -s -XPOST localhost:8080/api/jobs -H 'Content-Type: application/json' \
  -d '{"source":"Pictures/Trip","strategy":"auto"}' | jq -r .id)
curl -N localhost:8080/api/jobs/$JOB/events          # watch it live
curl -s localhost:8080/api/jobs/$JOB | jq '.categories'
curl -s -XPOST localhost:8080/api/jobs/$JOB/apply -H 'Content-Type: application/json' -d '{"mode":"move"}'
```

## AI prompt rules

```json
{
  "source": "Pictures/Trip",
  "strategy": "rules",
  "options": {
    "rules_prompt": "Landscapes go into landscapes/{date}; everything else into others/{date}",
    "output_dir": "Organized",
    "ai": {"model": null, "reasoning_effort": "low", "assist_batch": 12}
  }
}
```

A nonempty `rules_prompt` (max 4,000 characters) is required. Without configured AI the start request returns 400.
The backend compiles up to 12 rules before scanning. Nested relative destinations are validated strictly; path
traversal, absolute paths, duplicate destinations and multiple catch-alls fail the job. Dates resolve once at start.
The compiled rules are persisted in the snapshot request's internal `options._rules` for inspection; clients supply
only `rules_prompt`. All eligible thumbnails are matched; `ai_max_files` limits optional preset assist, not rule mode.
AI calls/tokens are included in usage. Matching failures produce `status: error`; Apply returns 409 for failed jobs.

## Culling recommendations

`options.quality.pick_profile`: `auto` (default), `portrait`, `fashion`, `landscape`, or `general`.
`pick_min_rating` defaults to 4.5 and `keeper_min_rating` to 4.0. Both accept 1–5, with Keepers no higher
than Picks (invalid bands return 422). Picks meet the upper threshold; Keepers meet the lower threshold and stay
below Picks; lower scores go to Maybe. Technical rejects and burst extras take precedence. Highly rated redundant
frames go to Similar alternatives. Quick settings persists these values.

Every ranked photo gets `pick` metadata: `{score, rating, profile, reasons, parts, picked}`.
`score` is 0–1; decimal `rating = round(1 + 4 * score, 2)` is on the 1–5 scale and determines the bands.
Parts include `tech`, relevant `expr`, `comp`, `light`, `aes`, `relative`, and measured `detail`, `balance`, `separation`.
`quality.score`, `quality.rating` and integer `quality.stars` derive from the same recommendation.
With `write_xmp`, integer ratings match `quality.stars`, picks receive Green labels and rejects receive rating -1/Red.
`picks_percent` is deprecated and ignored; the legacy positive `keeper_min_stars` overrides the keeper threshold
(capped at the Picks threshold). New clients should send the decimal fields and leave `keeper_min_stars: 0`.
Enabled reject checks remain authoritative. `/api/jobs/{id}/plan` manual changes update pick markers and XMP labels.
