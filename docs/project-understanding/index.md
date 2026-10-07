# Project understanding

This folder is the learning layer for the thesis app. It explains what each implemented story added, how the files connect, what commands to run and what concepts are worth understanding before moving on.

These notes are different from the formal thesis chapters. The thesis explains the academic work. This folder explains the code in beginner-friendly language.

## Reading Order

1. [Glossary](glossary.md).

2. [Commands](commands.md).

3. [01 - Local backend and database](01-local-backend-and-database.md).

4. [02 - Docker frontend service](02-docker-frontend-service.md).

5. [03 - Create research project](03-create-research-project.md).

6. [04 - Save YouTube search query](04-save-youtube-search-query.md).

7. [05 - Nginx and Gunicorn-ready local wiring](05-nginx-and-gunicorn-ready-local-wiring.md).

8. [06 - Generate draft YouTube API parameters](06-generate-draft-youtube-api-parameters.md).

9. [07 - Validate generated YouTube API parameters](07-validate-generated-youtube-api-parameters.md).

10. [08 - Build editable query parameter review screen](08-build-editable-query-parameter-review-screen.md).

11. [09 - Save approved parameters with validation feedback](09-save-approved-parameters-with-validation-feedback.md).

12. [10 - Create collection run model and status lifecycle](10-create-collection-run-model-and-status-lifecycle.md).

13. [11 - Start a collection run from a saved query](11-start-a-collection-run-from-a-saved-query.md).

14. [12 - Create API request log model and service wrapper](12-create-api-request-log-model-and-service-wrapper.md).

15. [13 - Store collection run counts, quota, timestamps and errors](13-store-collection-run-counts-quota-timestamps-and-errors.md).

16. [14 - Discover videos with YouTube search.list](14-discover-videos-with-youtube-search-list.md).

17. [15 - Add YouTube collection service tests](15-add-youtube-collection-service-tests.md).

18. [16 - Show request logs for each collection run](16-show-request-logs-for-each-collection-run.md).

19. [17 - Store video metadata and raw video payload](17-store-video-metadata-and-raw-video-payload.md).

20. [18 - Store channel metadata and raw channel payload](18-store-channel-metadata-and-raw-channel-payload.md).

21. [19 - Show video discovery summary](19-show-video-discovery-summary.md).

22. [20 - Store video statistics snapshots](20-store-video-statistics-snapshots.md).

23. [21 - Link collection runs to videos idempotently](21-link-collection-runs-to-videos-idempotently.md).

## Story notes

|                                                file                                                | story  | status |                                                                what it explains                                                                |
| :------------------------------------------------------------------------------------------------: | :----: | :----: | :--------------------------------------------------------------------------------------------------------------------------------------------: |
|                [01-local-backend-and-database.md](01-local-backend-and-database.md)                | US-001 |  Done  | Django backend scaffold, SQLite, PostgreSQL, Docker Compose, migrations, environment config, health checks and the `src/` nested-repo layout.  |
|                   [02-docker-frontend-service.md](02-docker-frontend-service.md)                   | US-002 |  Done  |           Dockerized React/Vite frontend, Compose `ui` service, Vite proxy, frontend health check, and frontend validation commands.           |
|     [05-nginx-and-gunicorn-ready-local-wiring.md](05-nginx-and-gunicorn-ready-local-wiring.md)     | US-003 |  Done  |        Gunicorn API startup, Nginx `web` service, front-door routing, Compose variables and production-style local validation commands.        |
|                   [03-create-research-project.md](03-create-research-project.md)                   | US-004 |  Done  |               Research project model, project API, owner fallback, frontend project workspace, and project validation commands.                |
|                 [04-save-youtube-search-query.md](04-save-youtube-search-query.md)                 | US-005 |  Done  |  Saved-query model, project-scoped query API, owner isolation, manual query form, stale-list protection and saved-query validation commands.   |
|     [06-generate-draft-youtube-api-parameters.md](06-generate-draft-youtube-api-parameters.md)     | US-006 |  Done  |     LLM query translation service, strict Structured Outputs schema, draft endpoint error statuses, read-only draft UI and offline tests.      |
| [07-validate-generated-youtube-api-parameters.md](07-validate-generated-youtube-api-parameters.md) | US-007 |  Done  | Pure parameter validator, allowlist and YouTube rules, RFC 3339 checks, the draft response's validation array and the read-only findings list. |
| [08-build-editable-query-parameter-review-screen.md](08-build-editable-query-parameter-review-screen.md) | US-008 |  Done  | Draft-to-form copy, one form as the review screen, the Order field, UTC/local date round trip and full structured params on save. |
| [09-save-approved-parameters-with-validation-feedback.md](09-save-approved-parameters-with-validation-feedback.md) | US-009 |  Done  | Save-time validation through the US-007 validator, all-or-nothing draft provenance, server-derived `query_source` and the rejected-save feedback. |
| [10-create-collection-run-model-and-status-lifecycle.md](10-create-collection-run-model-and-status-lifecycle.md) | US-010 |  Done  | `CollectionRun` model, five-state lifecycle in one `transition_to` method, compare-and-set against stale copies, PostgreSQL check constraints and delete rules. |
| [11-start-a-collection-run-from-a-saved-query.md](11-start-a-collection-run-from-a-saved-query.md) | US-011 |  Done  | Start endpoint, `effective_params` snapshot instead of a reference, re-validation at start, owner-scoped 404s and the per-card Start run button. |
| [13-store-collection-run-counts-quota-timestamps-and-errors.md](13-store-collection-run-counts-quota-timestamps-and-errors.md) | US-012 |  Done  | Run counters and `error_message`, totals kept in step with the logs (one writer, one transaction, `F()` updates), and the required message on `failed`. |
| [16-show-request-logs-for-each-collection-run.md](16-show-request-logs-for-each-collection-run.md) | US-014 |  Done  | Runs list and run-detail endpoints, the Collection runs panel with Refresh, nested request logs, and the late-response guards in the UI. |
| [12-create-api-request-log-model-and-service-wrapper.md](12-create-api-request-log-model-and-service-wrapper.md) | US-013 |  Done  | `ApiRequestLog` model, the single `call_youtube` wrapper, log-before-request, quota cost table, and keeping the key, IDs and response bodies out of the logs. |
| [14-discover-videos-with-youtube-search-list.md](14-discover-videos-with-youtube-search-list.md) | US-015 |  Done  | `collect_runs` command, claiming a run safely, quota-saving paging, shared `youtube_videos` rows refreshed per run, and HTML-unescaped snippet text. |
| [19-show-video-discovery-summary.md](19-show-video-discovery-summary.md) | US-016 |  Done  | The skipped counter (repeats and non-video results), counts read from the run row so they survive the purge, `discovered_videos`, and the Discovery section of the run detail. |
| [17-store-video-metadata-and-raw-video-payload.md](17-store-video-metadata-and-raw-video-payload.md) | US-017 |  Done  | The `videos.list` details step, batches of 50, field mapping and narrowing, `raw_payload`, `last_fetched_at` refresh and `total_videos_collected`. |
| [18-store-channel-metadata-and-raw-channel-payload.md](18-store-channel-metadata-and-raw-channel-payload.md) | US-018 |  Done  | The `channels.list` step, one channel row per channel updated in place, count parsing from strings, and video links that follow the latest data. |
| [20-store-video-statistics-snapshots.md](20-store-video-statistics-snapshots.md) | US-019 |  Done  | One statistics snapshot per video per run, added never overwritten, the conditional unique constraint, free `statistics` part, and the BIGINT bound on every count. |
| [21-link-collection-runs-to-videos-idempotently.md](21-link-collection-runs-to-videos-idempotently.md) | US-020 |  Done  | What idempotent means here, where the guarantee comes from (unique constraints plus `update_or_create`), and the two-run end-to-end proof. |
| [15-add-youtube-collection-service-tests.md](15-add-youtube-collection-service-tests.md) | US-034 |  Done  | Auditing existing tests for gaps, faking only `urlopen` so the real HTTP path runs, documented-shape fixtures, tests that fail instead of hang, and the repeated page-token fix. |

## How to use this folder

- Read the story page after a BMAD story is implemented and reviewed.

- Use [commands.md](commands.md) when you forget what a terminal command does.

- Use [glossary.md](glossary.md) when a repeated term feels fuzzy.

- Update the story page after review fixes so it describes the final reviewed code.

## Documentation rule

After each BMAD story is implemented, reviewed and fixed, add or update one story-specific page in this folder. The page should explain:

- what changed.

- why it was added.

- what each important file does.

- how the files connect.

- what commands to run.

- how to test manually.

- common errors and what they mean.

- beginner concepts to understand before the next story.
