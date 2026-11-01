# API reference

Base URL: `http://localhost:8080`. Interactive docs: **`/docs`** (Swagger UI) and `/redoc`.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/api/health` | | `{status, version, ai_available, model, library_ok, library_name, library_host_path, output_dir}` |
| GET | `/api/folders` | `?path=rel/path` | `{path, name, media_count, folders:[{name, path, media_count, has_children}]}` |
| GET | `/api/presets` | | `[CategorySet]` |
| GET | `/api/category-sets` | | custom `[CategorySet]` |
| POST | `/api/category-sets` | `{name, description?, categories:[{name, emoji?, prompts?}]}` | `201 CategorySet` (`422` on duplicate names) |
| PUT / DELETE | `/api/category-sets/{id}` | same / – | `CategorySet` / `204` |
| POST | `/api/jobs` | `JobRequest` | `201 {id}` · `409` if a sort is running · `400` bad folder · `404` unknown set |
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
  "strategy": "preset",           // preset | custom | auto | date
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
| `phase` | `phase`: scanning · analyzing · deduplicating · categorizing |
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
