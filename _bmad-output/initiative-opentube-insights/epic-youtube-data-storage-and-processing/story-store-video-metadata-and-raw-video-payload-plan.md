---
title: 'Store video metadata and raw video payload'
type: 'feature'
ticket: '1'
created: '2026-10-07'
status: 'built'
baseline_revision: '1236760c2cf7833f3df8507f47c50db09b241d56'
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

**Problem:** Discovery (US-015) stores only what `search.list` returns: an ID, a title, a truncated description and a publish date. The video metadata and raw payload the analysis needs are not stored (US-017).

**Approach:** After discovery, `collect_run` fetches details for the run's videos with `videos.list` (`part=snippet,contentDetails`), in batches of up to 50 IDs per request, all through `call_youtube`. Each returned item fills the remaining `youtube_videos` metadata columns, stores the whole item as `raw_payload`, and refreshes `last_fetched_at`, which starts the 30-day window. The run counts the videos it collected.

## Boundaries & Constraints

**Always:**
- **New columns:** `YouTubeVideo` gains `duration_iso8601`, `resolution`, `caption_status`, `default_language`, `default_audio_language`, `category_id`, `tags` (`JSONField(default=list)`) and `raw_payload` (`JSONField(null=True, blank=True)`). Types and nullability match `docs/database_schema.md`.
- **Field mapping:**
  - From `snippet`: `title`, `description` (the full text, which replaces the truncated search one), `youtube_published_at`, `live_broadcast_content`, `tags`, `category_id`, `default_language` and `default_audio_language`.
  - From `contentDetails`: `duration_iso8601` (`duration`), `resolution` (`definition`, e.g. `hd`) and `caption_status` (`caption`, `"true"`/`"false"`).
  - Values are stored as YouTube sends them. A missing field becomes null, or `[]` for tags. A wrong-typed field is ignored the same way.
- **Request shape:** requests use the `id` param (comma-joined), which `call_youtube` already logs as `{"redacted_count": n}`. One request per 50 IDs. No request is sent when the run discovered nothing.
- **Run counting:** `total_videos_collected` is the number of the run's videos updated from a `videos.list` item, written once at the end of the step, as `total_videos_discovered` is.
  - A discovered video absent from the response (deleted or private) is not counted and keeps its search data.
  - Re-collecting a known video refreshes its payload and `last_fetched_at`.
- **Failure:** a failing `videos.list` call fails the run through the existing `collect_run` handlers. Discovered links and any details already stored stay.
- **Tests:** no test reaches `googleapis.com`. Validated on Compose PostgreSQL.

**Never:**
- No `statistics` part and no snapshots (US-019).
- No channels and no `channel` FK (US-018).
- No cleaning or normalization (US-024).
- No purge (US-040).
- No UI change.
- No separate command: details are part of a collection run.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Details stored | run discovers 3 videos; `videos.list` returns 3 items | one `videos.list` request (after the search) with `id` holding the 3 IDs and `part=snippet,contentDetails`; every new column filled; `raw_payload` equals the item; title and description from `videos.list`; `total_videos_collected` 3; run `completed`; quota 100 + 1 | No error expected |
| Batching | 60 discovered videos | two `videos.list` requests (50 + 10 IDs), each logged with `id` as `{"redacted_count": 50}` and `{"redacted_count": 10}` | No error expected |
| Missing video | 3 discovered, response has 2 | 2 updated; the third keeps its search data with `raw_payload` null; `total_videos_collected` 2 | No error expected |
| Sparse item | item with no `tags`, `defaultLanguage` or `contentDetails` | `tags` `[]`; missing fields null; still counted | No error expected |
| Re-collect | video already holds an old `raw_payload` and `last_fetched_at` | both replaced by the new fetch | No error expected |
| Nothing discovered | search returns 0 items | no `videos.list` request; `total_videos_collected` 0; `completed` | No error expected |
| Details failure | `videos.list` returns HTTP 403 | run `failed`, `error_message` `HTTP 403: quotaExceeded`; links and earlier details kept; `total_videos_collected` = videos updated before the failure | logged as today |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` `YouTubeVideo` -- add the eight fields. Generate `0009` with `makemigrations core`.
- `src/api/core/collection.py` -- add `_collect_details(run, *, api_key, transport)`. `collect_run` calls it after `_discover_videos` inside the same `try`, so the existing `YouTubeApiError` and `Exception` handlers apply.
  - Read the run's video IDs from `run.run_videos` (in `discovered_at` order) and chunk them by 50.
  - Write `total_videos_collected` in a `finally`, as `_discover_videos` does for `total_videos_discovered`.
  - Reuse the typed-narrowing style of `_store_video` (a `text(key)` helper; `isinstance` checks on untrusted JSON).
  - Match items to rows by `item["id"]`.
- `src/api/core/youtube_client.py` -- no change. `videos.list` (cost 1) is already in `QUOTA_COSTS`, and `id` is already redacted.
- `src/api/core/admin.py` `YouTubeVideoAdmin` -- show the new fields (still read-only via `ReadOnlyAdmin`).
- `src/api/core/tests.py` -- extend `CollectRunTests`. Its `transport(pages)` is keyed by `pageToken`, so widen the fake to route by the URL path (`/search` vs `/videos`). Add a documented-shape `videos.list` item helper next to `_search_items`. Update the existing collector and end-to-end tests that assume search is the only call: give their fakes a `/videos` response, and adjust request counts and quota where asserted.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/models.py` + migration `0009` -- the eight columns.
- [x] `src/api/core/collection.py` -- `_collect_details` and the run count.
- [x] `src/api/core/admin.py` -- show the new fields.
- [x] `src/api/core/tests.py` -- one test per matrix row, plus updating existing tests for the extra request.

**Acceptance Criteria:**
- Given the batching test, when the chunk size is raised above 50, then the test fails.
- Given the details-stored test, when `raw_payload` is saved as anything other than the exact item, then the test fails.
- Given an end-to-end test (`urlopen` stubbed), when the run collects, then it sends a GET to `https://www.googleapis.com/youtube/v3/videos` with `part=snippet,contentDetails` after the search requests.

## Implementation Notes

- Migration is `0009_youtubevideo_details.py` (renamed from the auto-generated name).
- A `videos.list` item with no string `snippet.title` keeps the search title, because `title` is NOT NULL; every other missing field becomes null as specified.
- The fake transport's `/videos` default answers with no items, so existing search-only tests keep asserting search data; new tests pass a `details(ids)` function. The end-to-end fake serves `YOUTUBE_VIDEOS_RESPONSE` once.
- Mutation-checked: chunk size 51, a modified `raw_payload`, skipping `_collect_details`, not refreshing `last_fetched_at`, and a request on an empty run each fail at least one test.
- Orchestrator check: full suite 160 OK on PostgreSQL, `makemigrations --check` clean. Thesis baseline `6674c3517b3152f46cfd8b3a7f63b314b95997da`.
- Review patches (pass 1) applied: `raw_payload` test compares a fresh item; `tags` keeps only strings; batch tests compare sorted IDs. Full suite 160 OK on PostgreSQL.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 5, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `raw_payload` assertion compares against the served dict object, so in-place mutation would pass | low | patch | Confirmed: the fake returns the same objects; no JSON round-trip in `call_youtube`. Compare against a fresh `_video_item`. |
| `tags` elements not type-checked | low | patch | Confirmed; narrow at the boundary per AGENTS.md: keep `str` elements; add a mixed-list case. |
| Batch tests assert exact order, but ordering is by `discovered_at` only (ties possible within a page) | low | patch | Confirmed; compare sorted IDs per batch. Production order within a batch does not matter. |
| Details-failure test supplies the `HTTP 403: quotaExceeded` text it then asserts | low | reject | The behavior under test is propagation: run failed, earlier details kept, later batches skipped. Message parsing is endpoint-independent in `_get_json` and covered on the real path by `test_quota_error_fails_the_run_with_reason_codes_only`. |
| Over-long string or impossible `publishedAt` raises `DataError`/`ValueError` and fails the run | low | reject | Real YouTube values fit the columns; same trade-off accepted for `_store_video` in US-015; the fix adds per-field guards. |

## Design Notes

Details belong to the run, not a separate command. They cost 1 unit per 50 videos (100 for a page of search), and one `collect_runs` call should leave a complete dataset.

`statistics` is deliberately left out of `part` even though it costs nothing extra. US-019 stores statistics as snapshots, and adding the part then keeps this story's payload contract simple.

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.

**Manual checks:**
- With a real key: start a run with cap 5, run `collect_runs`, then open a video in `/admin/`. Duration, definition, tags and `raw_payload` are filled, and the run's request logs show one `search.list` and one `videos.list` row.
