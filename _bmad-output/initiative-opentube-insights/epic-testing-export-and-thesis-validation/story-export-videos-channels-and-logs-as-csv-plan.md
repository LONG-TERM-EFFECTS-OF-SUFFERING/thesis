---
title: 'Export videos, channels and logs as CSV'
type: 'feature'
ticket: '1'
created: '2026-10-09'
status: 'done'
baseline_revision: '50a9ab96b43854495e248920434350783a403f81'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context:
  - '{project-root}/docs/database_schema.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A researcher cannot take collected data out of the app to cite it or continue the analysis elsewhere, and nothing tells them when that data must be deleted under the 30-day policy (US-031).

**Approach:** Add three project-level CSV downloads: videos, channels and request logs. Each row carries its own collection date and deletion date, derived from the same rule the purge applies. The downloads are plain links in the Results panel.

## Boundaries & Constraints

**Always:**
- **Endpoints:** `GET /api/projects/<p>/export/videos.csv`, `.../channels.csv` and `.../request-logs.csv`.
  - Owner-scoped like every project endpoint: another owner's or a missing project is 404.
  - Response: `Content-Type: text/csv; charset=utf-8` and `Content-Disposition: attachment; filename="<kind>-<project id>-<YYYY-MM-DD export date, UTC>.csv"`.
  - Written with Python's `csv` module.
- **Rows:**
  - **videos:** the distinct videos this project's runs linked, ordered by title then id.
  - **channels:** the distinct channels of those videos, ordered by title then id.
  - **request logs:** every log of this project's runs, ordered by run `created_at`, then `request_sequence`.
  - An empty export still has its header row.
- **Columns:** the model's own scalar fields, by their field names, with no `raw_payload` (that is US-032).
  - Videos add `youtube_channel_id`.
  - Logs add `collection_run_id`; `request_params` is serialized as JSON text.
  - `tags` is JSON text.
  - Every timestamp is ISO 8601 UTC.
- **Dates, in every row** (both always present as columns):
  - `collected_at`: `last_fetched_at` for videos and channels, `started_at` for logs.
  - `delete_by`: `last_fetched_at + RETENTION_DAYS` (imported from `core.purge`, never restated) for videos and channels. On that instant the purge's strict cutoff makes the row eligible for deletion.
  - For logs, `delete_by` is empty, because the purge keeps request logs (US-040). This is stated in the UI next to the link.
- **UI:**
  - The Results panel shows an "Export" group with three native `<a href download>` links for the active project, built from the existing API base helper.
  - One line explains the two date columns and that logs are kept.
- **Tests:** API tests parse the CSV with `csv.DictReader` and assert the header, rows, scoping, ordering and the two date columns. No network.
- Validated on Compose PostgreSQL. No migrations and no new dependencies.

**Decisions** (approved by the human on 2026-10-09):
- **Spreadsheet-safe CSV:** every cell whose text starts with `=`, `+`, `-`, `@`, a tab or a carriage return is prefixed with `'` (the OWASP CSV-injection advice). The file starts with a UTF-8 byte-order mark, so Excel shows accents correctly. The UI line and the story page say both: a title like "-5 reasons" exports as "'-5 reasons", and pandas reads the file with `encoding="utf-8-sig"`. The escaping is one pure, tested helper applied to every cell.

**Never:**
- No raw payloads, comments, sentiment or statistics snapshots (US-032).
- No US-029 results filters on exports.
- No JSON format.
- No background jobs, zip archives or file storage on the server.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Videos | 2 videos linked by this project's runs (one linked by two runs), 1 linked only by another project | 2 rows, title order, with `collected_at` = `last_fetched_at` and `delete_by` = +30 days | No error expected |
| Channels | those videos share one channel; another project's video has another channel | 1 row | No error expected |
| Logs | 2 runs with 3 logs; another project's run has logs | 3 rows in run then sequence order; `collection_run_id` set; `delete_by` empty | No error expected |
| Empty | a project with no runs | header row only, for all three | No error expected |
| Foreign project | another owner's project id | no data | 404 |
| Unicode | a title with accents and emoji | the body starts with the UTF-8 BOM; decoded with `utf-8-sig`, the title round-trips exactly through `csv.DictReader` | No error expected |
| Formula cell | a title `=HYPERLINK("x")`, a description `-5 reasons`, a title `normal` | `'=HYPERLINK("x")`, `'-5 reasons`, `normal` | No error expected |
| Purged | the project's videos were purged | videos and channels header only; logs still exported | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/views.py`:
  - `ProjectOwnerMixin.get_project` scopes to the owner.
  - `ResultsSummaryView` shows the project-scoped video query (`YouTubeVideo.objects.filter(run_links__collection_run__project=project)`) and the channel query through the videos. Reuse those shapes with `.distinct()`.
  - Add one small CSV view per kind, or one view with a kind map, returning Django's `HttpResponse`.
- `src/api/core/purge.py`: `RETENTION_DAYS`. Import it; never restate `30`.
- `src/api/core/urls.py`: three routes beside `project-results-videos`, named `project-export-videos`, `project-export-channels` and `project-export-request-logs`.
- `src/api/core/models.py`: read-only. The fields are `YouTubeVideo`, `YouTubeChannel` and `ApiRequestLog`; `last_fetched_at` starts the retention window.
- `src/api/core/tests.py`: add `CsvExportApiTests`. `ResultsSummaryApiTests` has helpers for runs, videos and links.
- `src/ui/src/apiConfig.ts`: `buildApiUrl(baseUrl, path)`, which `apiClient.ts` already calls with the Vite base. Build the link with it, never hardcoded.
- `src/ui/src/App.tsx`: the Results panel (`results-panel`). Add the Export group under the filters form, only when a project is active.
- `src/ui/src/apiClient.ts` + `tests/`: a tiny pure `exportUrl(projectId, kind)` beside the other endpoint builders, tested.
- `src/api/README.md`: one `curl` example for an export, beside the existing ones (paths as if `src/api` were the root).

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/views.py` + `core/urls.py` -- the three CSV endpoints.
- [x] `src/api/core/tests.py` -- one test per I/O row.
- [x] `src/ui/src/apiClient.ts` + test -- `exportUrl`.
- [x] `src/api/README.md` -- one export example.
- [x] `src/ui/src/App.tsx` -- the Export links and the explanatory line.

**Acceptance Criteria:**
- Given the videos test, when `delete_by` is computed with a hardcoded number of days other than `RETENTION_DAYS`, then the test fails.
- Given the videos test, when the `.distinct()` is dropped, then the video linked by two runs appears twice and the test fails.
- Given any export, when it is opened with `csv.DictReader`, then the first row's keys are exactly the documented header.

## Implementation Notes

- Baselines: API `50a9ab96b43854495e248920434350783a403f81` (frontmatter), UI `779c75a262b624eab2eca3fb48770cd4c1feb637`, thesis `1635ae4f8c52f8320c5a04345034d0084bcbf0a6`. Both app repos are on `feature/US-031`.
- One `ProjectCsvExportView` with `kind` set per route through `as_view(kind=...)`; `EXPORT_COLUMNS` holds each kind's columns. `csv_cell(value)` renders None as empty, datetimes as ISO 8601 UTC (`+00:00`), lists and dicts as JSON (`ensure_ascii=False`), and quotes formula-leading text. The BOM is written first, and the header is always written. Logs are ordered by run `created_at`, run id, then `request_sequence`.
- `delete_by` is the instant **after** which the purge deletes the row (its cutoff is strict `<`). The purged test purges at `delete_by + 1µs`. The README and the UI line say "after".
- Known limit: DRF content negotiation answers 406 to a request whose only `Accept` is `text/csv`. Browsers, curl and pandas send `*/*` or nothing.
- Mutation checks (implementer), each failing a test: dropping `.distinct()`, `days=29`, no formula escaping, no BOM, logs ordered by run id, logs or channels not scoped to the project, logs given a `delete_by`, a wrong `exportUrl` path.
- Review patches (pass 1) applied, see the triage log. Re-verified: backend 348 OK on PostgreSQL, migrations clean; UI 89 pass, build and lint clean.

- Orchestrator check: backend 347 OK on PostgreSQL (the 10 new `CsvExportApiTests` and `CsvCellTests` all ran), migrations clean; UI 89 pass, build and lint clean. All 8 matrix rows are covered.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 3, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Logs `order_by(..., "collection_run", ...)` expands to `CollectionRun.Meta.ordering` (`-created_at`), so the SQL has no run-id tiebreak and two runs with equal `created_at` interleave their logs | low | patch | Confirmed (Django orders by a relation through the related model's default ordering). Now `collection_run_id`; `test_request_logs_of_runs_created_together_stay_grouped` fails with the old ordering. |
| The approved every-cell escaping also changes identifiers (a YouTube video id can start with `-`), so a join on `youtube_video_id` silently misses those rows, and neither the README nor the UI says so | medium | patch | Confirmed: base64url ids can start with `-`. Behavior kept as decided (every cell); the README and the UI hint now say identifiers are escaped too and to strip a leading `'` before joining. |
| Channel ordering untested: only one channel is in scope | low | patch | Confirmed. A second in-scope channel, created later and titled before `Shared`, is asserted first; fails without the `order_by`. Also found while patching: the videos test passed without its `order_by` (Alpha was created first), so `seed_videos` now creates Beta first; it fails without the `order_by`. |
| The Export hint lists only =, +, - and @, and does not say the exports ignore the filters above it | low | patch | Confirmed. The hint lists the tab and carriage return and says the exports cover the whole project. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: No changes detected.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass.

**Manual checks:**
- With collected data, click each Export link: the browser downloads a CSV whose rows match the run detail, with `collected_at` and `delete_by` 30 days apart.
