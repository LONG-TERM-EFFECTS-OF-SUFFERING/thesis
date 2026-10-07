---
title: 'Collect top-level comments for selected videos'
type: 'feature'
ticket: '1'
created: '2026-10-07'
status: 'built'
baseline_revision: '40a9a2b1de7f87818fbd2f388bd6b66d66c779f8'
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

**Problem:** Audience reaction is not collected. No comments are stored, so sentiment analysis (US-025) has no input (US-021).

**Approach:** Add `YouTubeComment` and `CollectionRunComment`, as `docs/database_schema.md` defines them. A comment step in `collect_run`, after channels, pages through `commentThreads.list` for the selected videos via `call_youtube`. Each top-level comment is stored with its fetch timestamp and raw payload and linked to its video and to the run.

## Boundaries & Constraints

**Always:**
- **Tables:**
  - `YouTubeComment` (`youtube_comments`) has a unique `youtube_comment_id`, a `CASCADE` FK to `video`, and a nullable self `parent_comment` FK.
  - `comment_level` is `top_level` or `reply`. A `CheckConstraint` requires top-level rows to have no parent and replies to have one.
  - `CollectionRunComment` (`collection_run_comments`) is unique per (`collection_run`, `comment`) and carries `page_number` and `thread_position`.
- **Request:** `commentThreads.list` with `part=snippet`, `videoId`, `textFormat=plainText`, `order=time` (the API default, chronological, the most repeatable), `maxResults=min(100, comments still needed)` and `pageToken`. It costs 1 unit per page. `videoId` is already logged as a redacted count.
- **Field mapping** (from `item.snippet.topLevelComment`):
  - `youtube_comment_id` (its `id`), `author_channel_id` (`authorChannelId.value`), `like_count`, `youtube_published_at` and `youtube_updated_at`.
  - `text_display` is `textDisplay`. `text_original` is `textOriginal` when YouTube returns it (only for the comment's author), else `textDisplay`.
  - `total_reply_count` comes from the thread's `snippet.totalReplyCount`. `raw_payload` is the whole thread item.
  - `first_collected_at` is set once. `last_fetched_at` is refreshed on every fetch, which starts the 30-day window.
  - Counts are parsed as ints with `bool` rejected (AGENTS.md).
- **Reuse and counting:** a known comment is updated, not duplicated, and linked once per run. `total_comments_collected` counts the run's distinct linked top-level comments and is written once, in a `finally`.
- **Paging:** stops at the per-video limit, a missing `nextPageToken`, an empty page or a repeated token (the US-034 lesson).
- **Comments disabled:** a `commentsDisabled` 403 skips that video and the run continues. Any other `YouTubeApiError` fails the run through the existing handlers, and what was stored stays.
- **Tests:** no test reaches `googleapis.com`. Validated on Compose PostgreSQL.

**Decisions** (approved by the human on 2026-10-07; recorded late because the first insert did not apply):
- **Selected videos:** every video the run collected details for in this run (US-017), when the run has a comment limit. There is no separate selection screen.
- **The limit:** a new optional `SavedQuery.max_comments_per_video` (`PositiveIntegerField(null=True, blank=True)`, at least 1 when set). It is set in the save form and copied at start into `effective_params["max_comments_per_video"]` and `CollectionRun.requested_comment_limit`.
- **Its meaning:** up to N top-level comments **per video**. A null limit means the comment step sends no request at all.
- **Schema doc:** gains a `saved_queries.max_comments_per_video` row, and `requested_comment_limit` is reworded to "per video".

**Never:**
- No replies: the `replies` part is not requested and no reply rows are written (US-022).
- No resume of an interrupted run (US-022).
- No sentiment (US-025).
- No purge (US-040).
- No comment display in the UI (US-026 and later).
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Comments stored | selected video with limit 150; page 1 = 100 threads + token; page 2 = 50 threads | two requests, the second with `maxResults=50`; 150 comment rows, `comment_level` `top_level`, every field mapped; 150 links with page and position; `total_comments_collected` 150 | No error expected |
| Text fallback | thread without `textOriginal` | `text_original` = `textDisplay` | No error expected |
| Comments disabled | `commentThreads.list` 403 `commentsDisabled` for video A; video B fine | A skipped with no rows; B's comments stored; run `completed` | logged as a request-log row with its error |
| Other API error | 403 `quotaExceeded` on a comment page | run `failed`; comments stored before it kept | existing handlers |
| Known comment | comment already stored by an earlier run | same row updated (`last_fetched_at`, `like_count`, `raw_payload`), `first_collected_at` unchanged; a new link for this run | No error expected |
| No limit | saved query without `max_comments_per_video` | run's `requested_comment_limit` null; no `commentThreads.list` request; `total_comments_collected` 0 | No error expected |
| Limit wiring | saved query with `max_comments_per_video` 20, run started | run's `requested_comment_limit` 20 and `effective_params.max_comments_per_video` 20; editing the query later leaves both unchanged | No error expected |
| Bad limit | save with `max_comments_per_video` 0, -1 or `true` | not saved | 400 |
| Check constraint | a top-level row with a parent, or a reply without one | not saved | `IntegrityError` |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` -- add `YouTubeComment` and `CollectionRunComment` after `VideoStatisticsSnapshot`. Generate `0013`.
- `src/api/core/youtube_client.py` -- `YouTubeApiError` gains a `reasons: tuple[str, ...]` attribute, filled in `_get_json` from the same parsing `_http_error_message` already does, so the collector can test for `commentsDisabled` without string matching. `commentThreads.list` (cost 1) and the `videoId` redaction already exist.
- `src/api/core/collection.py` -- `_collect_comments(run, ...)` after `_collect_channels`, inside the same `try`. Reuse `_count`, the `text()` narrowing helpers, the repeated-token guard and the `finally`-written count pattern.
- `src/api/core/admin.py` -- read-only registration of both models.
- `src/api/core/tests.py` -- a `/commentThreads` route in the `CollectRunTests` fake, a documented-shape `_comment_thread` helper, one test per matrix row, and end-to-end updates for any extra request.
- `src/api/core/models.py` `SavedQuery`, `CollectionRun` -- add `max_comments_per_video` and `requested_comment_limit` (`0013` covers them too).
- `src/api/core/serializers.py` `SavedQuerySerializer` -- add the field, with a validation mirroring `validate_max_videos_to_discover` (≥ 1, `bool` rejected). `CollectionRunSerializer` exposes `requested_comment_limit`.
- `src/api/core/views.py` `CollectionRunStartView.post` -- add `"max_comments_per_video"` to the `effective_params` dict and set `requested_comment_limit` from the same value. The collector reads `run.requested_comment_limit`.
- `src/ui/src/apiClient.ts`, `src/ui/src/savedQueryForm.ts`, `src/ui/src/App.tsx` -- copy how `max_videos_to_discover` / `maxVideosToDiscover` is typed, built and rendered (a number input "Comments per video", empty means none). Update `tests/savedQueryForm.test.ts` and `tests/savedQueryApi.test.ts`.
- `docs/database_schema.md` (thesis repo, separate docs commit) -- the two doc changes in Decisions.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/models.py` + migration `0013` -- the two tables and the check constraint.
- [x] `src/api/core/youtube_client.py` -- `YouTubeApiError.reasons`.
- [x] `src/api/core/collection.py` -- the comment step.
- [x] `src/api/core/serializers.py`, `views.py` -- the saved-query field, its validation and the copy at start.
- [x] `src/ui/src/apiClient.ts`, `savedQueryForm.ts`, `App.tsx` + tests -- the form field.
- [x] `docs/database_schema.md` -- the two doc changes.
- [x] `src/api/core/admin.py`, `src/api/core/tests.py` -- registration and tests.

**Acceptance Criteria:**
- Given the comments-disabled test, when the collector treats `commentsDisabled` like any other error, then the test fails because the run is failed.
- Given the known-comment test, when `first_collected_at` is overwritten on re-fetch, then the test fails.

## Implementation Notes

- `commentThreads.list` sends `likeCount` and `totalReplyCount` as JSON numbers, not the decimal strings `_count` parses (and rejects ints for). Added `_json_count` in `collection.py`: `int` only, `bool` rejected, 0 to the column ceiling (`MAX_BIGINT` for `like_count`, `MAX_INTEGER` for `total_reply_count`), else null; a null `like_count` is stored as its default 0.
- `_http_error_message` became `_http_error_reasons` (returns the tuple); `_get_json` builds the same `HTTP <status>: <reasons>` message from it and passes `reasons=` to `YouTubeApiError`.
- `bool` for `max_comments_per_video` is already rejected by DRF's `IntegerField` (`int("True")` fails); the validator adds only the >= 1 bound. Tested with `true`.
- Review fix: `_collect_details` now also returns the videos it gave details in this run (discovery order); `_collect_comments` requests comments only for those, per the Decision. Paging keeps a per-video set of sent tokens, so an A→B→A cycle stops.
- Comment tests live in `CollectRunTests` (`collect_comments` helper). One extra end-to-end test (`CollectRunsEndToEndTests`) drives a real `commentsDisabled` HTTP 403 body through `_get_json`, so the `reasons` parsing is covered on the unfaked path.
- Mutations checked: treating `commentsDisabled` as any error, overwriting `first_collected_at`, and dropping the repeated-token guard each fail their test.
- `docs/database_schema.md`: added the `saved_queries.max_comments_per_video` row and described `effective_params.max_comments_per_video` / `requested_comment_limit` in `collection_runs` (Prettier reflowed that table's column widths).
- UI `CollectionRun` type does not declare `requested_comment_limit`; no screen shows it yet (US-026 and later).
- Review patches (pass 1) applied: comments only for videos collected in this run; per-video set of sent tokens; admin selects both FKs; UI form test proves the limit survives; docstring reflowed. Backend 206 OK on PostgreSQL; UI 60 pass, build and lint clean. UI baseline `adf84ba72dc053a28d1c9a650ce3374f12e0c7b8`; thesis baseline `4d57d997c316af48fb7cc5732e282d200d3a68c7`.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 2, low 3, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Comments requested for every linked video, not only those collected in this run; a deleted video's 404 fails the run | medium | patch | Confirmed: `_collect_comments` iterates `run.run_videos`. Deviates from the Decision, which was missing from the frozen block when implementation started (orchestrator's failed insert). Fix: `_collect_details` returns the videos it updated; comment tests get a details fake; new test for a video absent from `videos.list`. |
| Repeated-token guard only catches an immediate repeat; an A→B→A cycle of known comments loops until quota runs out | medium | patch | Confirmed: `token == page_token` compares only the last token, and `linked` cannot grow on known comments. Fix: per-video set of sent tokens; cycle test that fails rather than hangs. |
| `CollectionRunCommentAdmin` misses `collection_run` in `list_select_related` | low | patch | Confirmed against `list_display`; direct correction, as in `VideoStatisticsSnapshotAdmin`. |
| `applyDraftToForm` test keeps an empty limit, so it passes even if the field were reset | low | patch | Confirmed; AGENTS.md "passes for the wrong reason" pitfall. Give `namedForm` a non-empty limit. |
| `collect_run` docstring has a broken wrap | low | patch | Confirmed; reflow. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass.

**Manual checks:**
- Save a query with a video cap of 2 and a comment limit of 20, then collect. `/admin/` shows up to 40 comments, each linked to its video and the run, and the run's logs show the `commentThreads.list` rows.
