---
title: 'Discover videos with YouTube search.list'
type: 'feature'
ticket: '6'
created: '2026-10-05'
status: 'done'
baseline_revision: '3079f6f47fc12a1981c876cfd7e0e2e4eeed13c4'
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

**Problem:** A started run stays `pending` forever. Nothing executes it, so no videos are ever discovered (US-015).

**Approach:** Add a collector that takes a `pending` run and moves it to `running`. It pages through `search.list` via `call_youtube`, using the run's `effective_params`. For each discovered video it stores the YouTube video ID with its fetch timestamp (`youtube_videos`) and the link to the run (`collection_run_videos`). It stops as soon as the cap is reached or YouTube has no more pages, then completes the run, or fails it with an error message.

## Boundaries & Constraints

**Always:** Every YouTube call goes through `call_youtube(run, "search.list", ...)`. Requests are exactly `effective_params["search_list"]` plus `pageToken` and a per-page `maxResults`.
- The per-page `maxResults` is `min(search_list["maxResults"], videos still needed)`. No request asks for more than the cap still needs.
- Paging stops when the cap is reached, when there is no `nextPageToken`, when a page returns no items, or when the per-page size would be 0.
- Status changes only through `transition_to`: `pending → running → completed`, or `running → failed` with `error_message`.
  - On `YouTubeApiError` the message is `str(exc)`.
  - On any other exception it is the exception class name, logged with `logger.exception`.
  - Videos found before the failure stay linked.
- A video already in `youtube_videos` (from another run) is reused, and its `title` and `last_fetched_at` are refreshed, because search just re-fetched it. A video seen twice in one run is linked once.
- `total_videos_discovered` = the number of distinct videos linked to the run. It is written with `F()` or as the final count, never by read-modify-write.
- `YouTubeVideo` and `CollectionRunVideo` columns match `docs/database_schema.md` for the columns this story adds.
- No test reaches `googleapis.com`: inject `transport`. Validated on Compose PostgreSQL.

**Decisions:** The runner is a management command, `manage.py collect_runs`, which collects every `pending` run oldest-first (`created_at`); the start endpoint keeps returning `pending`. A null `max_videos_to_discover` means one page of `search_list["maxResults"]`. `total_videos_discovered` counts distinct videos, and no duplicate counter is stored (US-016 adds one). An empty `YOUTUBE_API_KEY` makes the command raise `CommandError("YOUTUBE_API_KEY is not configured.")` before touching any run.

**Never:** No `videos.list`, channels, `channel` FK, tags, duration or `raw_payload` filling (US-017, US-018). No summary UI or run detail page (US-014, US-016). No purge (US-040). No Celery, threads or new dependencies. Never re-run a run that is not `pending`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path, cap 60, page size 50 | page 1: 50 items + token; page 2: 10 items | two requests, the second with `maxResults=10`; 60 links (`page_number` 1 and 2); run `completed`; `total_videos_discovered` 60; quota 200 | No error expected |
| Last page | page 1 has 7 items and no `nextPageToken` | one request; 7 links; `completed` | No error expected |
| Empty result | 0 items | one request; 0 links; `completed` | No error expected |
| Duplicate in run | the same videoId on pages 1 and 2 | linked once; `total_videos_discovered` counts it once | No error expected |
| Known video | videoId already stored by an earlier run | same `youtube_videos` row; `last_fetched_at` and `title` updated; new link | No error expected |
| API failure | page 2 returns HTTP 403 | run `failed`, `error_message` `HTTP 403: quotaExceeded`; page-1 links kept | none raised by the collector; logged |
| Unexpected error | transport raises `RuntimeError` | run `failed`, `error_message` `RuntimeError` | `logger.exception` |
| Not pending | run already `running`/`completed`, or claimed by another worker | no requests, run unchanged | skipped |
| No cap | `max_videos_to_discover` null, 50 items + token | one request only; `completed` | No error expected |
| Missing key | `YOUTUBE_API_KEY` empty | no run touched | `CommandError` |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` -- add `YouTubeVideo` (`youtube_videos`): `youtube_video_id` (unique, 32), `title`, `description`, `youtube_published_at`, `live_broadcast_content`, `last_fetched_at` (`default=timezone.now`), `created_at` and `updated_at`. Add `CollectionRunVideo` (`collection_run_videos`): both FKs `CASCADE`, `page_number` and `discovered_at`, with unique (`collection_run`, `video`). The other `youtube_videos` columns and `channel` belong to US-017 and US-018. Generate `0008`.
- `src/api/core/collection.py` (new) -- `collect_run(run, *, api_key, transport=None) -> None`. Reuses `call_youtube`, `YouTubeApiError` and `CollectionRun.transition_to`. A `ValueError` from the claim (`pending → running`) means another worker already took the run: skip it.
- Search item shape: `items[].id.videoId`, `items[].snippet.{title, description, publishedAt, liveBroadcastContent}`. Skip an item without a string `videoId`. Parse `publishedAt` with `django.utils.dateparse.parse_datetime`.
- `src/api/core/management/__init__.py`, `commands/__init__.py`, `commands/collect_runs.py` -- `Command.handle` loops over `CollectionRun.objects.filter(status="pending").order_by("created_at")` and calls `collect_run`, printing one line per run. `settings.YOUTUBE_API_KEY` is read there, not at import.
- `src/api/core/admin.py` -- register both models read-only (no add, change or delete), like `ApiRequestLogAdmin`.
- `src/api/core/tests.py` -- `CollectRunTests` with a fake transport that returns pages keyed by `pageToken`, one test per matrix row, plus a runner test.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/models.py` + migration `0008` -- the two models.
- [x] `src/api/core/collection.py` -- `collect_run`.
- [x] `src/api/core/management/commands/collect_runs.py` -- the runner.
- [x] `src/api/core/admin.py` -- read-only registration.
- [x] `src/api/core/tests.py` -- matrix rows plus the runner.

**Acceptance Criteria:**
- Given the happy-path test, when the per-page `maxResults` stops shrinking to the remaining cap, then a test fails, because it asserts the second request's `maxResults=10`.
- Given a run that has been collected, when the runner is invoked again, then no request is sent.

## Implementation Notes

- `collect_run` claims via `transition_to("running")` (a `ValueError` means skip), pages in `_discover_videos`, and writes `total_videos_discovered` once in a `finally` as the distinct-link count. `_search_params` type-checks the `effective_params` snapshot (bad shape → `ValueError` → run `failed`). `_store_video` uses `update_or_create` to refresh known videos.
- Admin: a `ReadOnlyAdmin` base (no add, change or delete) now backs `ApiRequestLogAdmin` and the two new models.
- Matrix audit: every row covered by `CollectRunTests` (13 tests, including the runner, a missing key, an item without `videoId` and `maxResults=0`); full suite 141 OK on PostgreSQL. Mutation-checked: removing the per-page shrink fails the happy path. Known gap: a run that crashes between claim and finish stays `running`. Thesis baseline: `7586811b7b7a6813e1684bde1437f93b9cedb140`.
- Review patches (pass 1) applied: a null cap stops after the first request whatever it returned; snippet title and description go through `html.unescape`. Full suite 142 OK on PostgreSQL.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 2, low 1, false 1, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Null cap: a short first page with `nextPageToken` sends a second request | medium | patch | Confirmed: `target = page_size` and the loop continues while `len(seen) < target`; breaks the one-page decision. Fix: stop after the first request when cap is None; test with a short page. |
| `snippet.title`/`description` stored HTML-escaped | medium | patch | Confirmed: search.list returns escaped snippet text and `_store_video` stores it verbatim on every refresh. Fix: `html.unescape`. |
| `ValueError` from the complete/fail `transition_to` escapes and aborts `collect_runs` if the run was cancelled mid-collection | false | reject | Unreachable today: no endpoint cancels a run and admin `status` is read-only, so a running row cannot change under the collector. Revisit when cancellation lands. |
| One malformed item (impossible date, `videoId` > 32, `liveBroadcastContent` > 20) fails the whole run | low | reject | YouTube video IDs are 11 chars and `publishedAt` is valid RFC 3339; unlikely in use, the fix adds per-field guards, and failing loudly on a malformed upstream payload is acceptable. |

## Design Notes

The claim `transition_to("running")` is a compare-and-set (US-010), so two runners can never collect the same run. 

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.

**Manual checks:**
- With a real `YOUTUBE_API_KEY` in `src/api/.env`: start a run in the UI with cap 60, run `venv/bin/python manage.py collect_runs`, then check `/admin/`. The run is `completed` with 2 request logs (quota 200) and 60 run-video links.
