# Organize: Plan, Apply, Undo

## Requirements

### Requirement: REQ-ORG-1 Jobs and plans
Starting a sort SHALL create a background job, which runs: scan → analyze → dedupe → categorize → plan.
The finished job SHALL expose a plan made of
`{file_id, rel_path, kind, category, confidence, source, destination, duplicate_of?}`.
Building the plan SHALL NOT modify the library.

#### Scenario: Dry run
- WHEN a job finishes and the user does not press Apply
- THEN no file in the library has moved

### Requirement: REQ-ORG-2 Live progress
The job SHALL publish an ordered stream of events over Server-Sent Events (`GET /api/jobs/{id}/events`):
`phase`, `file` (discovered, with thumbnail URL and kind), `progress` (analyzed count), `categories`
(the final list of categories), `assign` (file → category), `stats`, `warning`, `done`, and `error`.
A client that connects late SHALL first receive every past event (replay), then live ones.

#### Scenario: Late subscriber
- WHEN a browser connects after 300 files have been discovered
- THEN it first receives those 300 `file` events in order

### Requirement: REQ-ORG-3 Apply
`POST /api/jobs/{id}/apply` SHALL carry out the plan in `move` (default) or `copy` mode. Destination folders
SHALL be created as needed. A name collision SHALL be resolved by adding ` (1)`, ` (2)`, … before the extension.
Files already at their destination SHALL be skipped. A job SHALL be applied at most once.

#### Scenario: Collision
- WHEN `Organized/Photos/Nature/a.jpg` already exists and another `a.jpg` goes there
- THEN the second one is saved as `a (1).jpg`

### Requirement: REQ-ORG-4 Journal
Every apply SHALL write `/data/journals/<run_id>.json` holding `{run_id, job_id, created_at (ISO-8601 UTC),
mode, source, ops:[{src, dst}]}`. Each op SHALL be written only after it succeeds.
A failed op SHALL be recorded in `failed` and SHALL NOT stop the apply.

### Requirement: REQ-ORG-5 Undo
`POST /api/runs/{run_id}/undo` SHALL reverse the ops in reverse order: move mode moves the file back,
and copy mode deletes the copy (only if it is unchanged since the copy). It SHALL then remove the folders it created that are now empty
and mark the journal as `undone`. An op whose `dst` no longer exists SHALL be reported and skipped.

#### Scenario: Full round trip
- WHEN the user applies and then undoes a run
- THEN every file is back at its original path, and `Organized/` is gone if it was created by that run

### Requirement: REQ-ORG-6 Run history
`GET /api/runs` SHALL list past runs (newest first) with their counts and status, so they can be undone later,
including after a container restart.
