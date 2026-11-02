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

## Automatic search tags

`options.auto_tags` defaults to true. Each plan item can include `tags: [{label, score, group, source}]`; source is
`local-ai` or `metadata`. Scores are heuristic strengths, not calibrated probabilities. Caches are per-model and
invalidated by file size/mtime or tag pipeline version. Tagging failure warns without preventing a sorting plan.

`GET /api/library/tags?folder=Trip&model=siglip2` returns `{tags:[{label,count}],tagged,indexed}`.
Search accepts repeated `tag` parameters (up to 12), with AND semantics and exact label/alias matching:
`GET /api/library/search?q=red+dress&folder=Trip&tag=red&tag=dress`. Results include stored tags; keyword/alias matches
boost semantic ranking. Folder validation applies to facets and search. Stale/missing-file tags are excluded.

## Social Media and advanced review

`strategy: preset, set_id: social-media` normalizes to Cull with `quality.social_media: true`. The recipe also exposes
this mode. Quality options add `social_format: portrait|square|vertical|landscape|original`, `social_weight: 0–0.5`
(default .25), `subject_prompt` (up to 300 characters), `preserve_unique` and `pareto_review` (both default true).
Social parts include crop, clarity, impact, contrast, color and social. Additional parts expose novelty, Pareto status,
gradient focus and artifact indicators. `burst.margin` records the strongest/runner-up score difference.
`quality.face_regions` contains normalized face boxes, focus and blink values for comparison; `eyes_open` and
`faces_considered` summarize the configured face rule.

Burst extras and high-rated similar alternatives keep their integer rating with a Yellow XMP label; technical rejects
remain -1/Red, and Picks Green. Applied plans expose `preview_path` so viewers open actual destinations; Undo restores
source preview paths. Search metadata is copied to Apply destinations, with original entries retained for Undo.
