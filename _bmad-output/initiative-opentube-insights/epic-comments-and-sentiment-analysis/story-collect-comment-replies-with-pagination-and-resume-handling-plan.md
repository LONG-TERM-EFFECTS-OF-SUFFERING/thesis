---
title: 'Collect comment replies with pagination and resume handling'
type: 'feature'
ticket: '2'
created: '2026-10-07'
status: 'built'
baseline_revision: '975a013b5d05c941b31dc616fee0197aad401d42'
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

**Problem:** Only top-level comments are collected, so conversations under them are lost. An interrupted collection also gives no reliable picture of what was stored (US-022).

**Approach:** After the top-level comment step, `collect_run` fetches replies with `comments.list` (`parentId`), paging through `call_youtube`, for the run's top-level comments that report replies. Each reply is stored as a `YouTubeComment` with `comment_level=reply` and `parent_comment` set, and linked to the run. An interrupted or failed run reports exactly what it stored, and running the query again completes the data without duplicates.

## Boundaries & Constraints

**Always:**
- **Request:** `comments.list` with `part=snippet`, `parentId`, `textFormat=plainText`, `maxResults=min(100, replies still needed)` and `pageToken`. It costs 1 unit per page, and `parentId` is already logged as a redacted count.
- **Which threads:** the top-level comments linked to **this run** whose stored `total_reply_count` is > 0. No request is sent for a thread with 0 replies.
- **Field mapping:** the same as US-021's `_store_comment` (`textOriginal` → `textDisplay` fallback, `_json_count`, `first_collected_at` kept, `last_fetched_at` refreshed, `raw_payload` = the comment item). In addition, `comment_level=reply`, `parent_comment` = the thread's row and `video` = the parent's video. `total_reply_count` stays null for replies.
- **Paging:** stops at the reply limit, a missing `nextPageToken`, an empty page or any token already sent for that thread (US-021's set guard).
- **Counting:** `total_replies_collected` counts the run's distinct linked replies, written once in a `finally`, so a failed run reports its true partial count.
- **Partial runs:** any failure fails the run through the existing handlers, and every reply stored before the failure stays and stays linked. A later run of the same query re-collects idempotently: known replies are updated, not duplicated, and the run gets its own links. This is the resume path.
- **Missing parent:** a `comments.list` 404 for one thread (the parent was deleted between steps) skips that thread, and the run continues, like `commentsDisabled` in US-021.
- **Tests:** no test reaches `googleapis.com`. Validated on Compose PostgreSQL.

**Decisions** (approved by the human on 2026-10-07):
- **Reply limit:** a new optional `SavedQuery.max_replies_per_comment` (`PositiveIntegerField(null=True, blank=True)`, at least 1 when set, `bool` rejected), wired exactly like US-021's `max_comments_per_video`.
  - It is set in the save form ("Replies per comment", empty means no replies).
  - At start it is copied into `effective_params["max_replies_per_comment"]` and a new `CollectionRun.requested_reply_limit` (`PositiveIntegerField(null=True, blank=True)`).
  - It means up to N replies per top-level comment. A null limit means the reply step sends no request.
- **Resume:** report partial plus re-run. A failed run stays `failed` (terminal, US-010), keeps everything it stored and reports true partial counts. Starting the same query again completes the data idempotently. No cursor state, and no resume flag.
- **Schema doc:** gains a `saved_queries.max_replies_per_comment` row and a `collection_runs.requested_reply_limit` row.

**Never:**
- No replies to replies (YouTube does not support them).
- No sentiment (US-025), no purge (US-040), no UI display of comments.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No limit | saved query without `max_replies_per_comment` | `requested_reply_limit` null; no `comments.list` request | No error expected |
| Limit wiring | saved query with `max_replies_per_comment` 10, run started | run's `requested_reply_limit` 10 and `effective_params.max_replies_per_comment` 10 | No error expected |
| Bad limit | save with `max_replies_per_comment` 0, -1 or `true` | not saved | 400 |
| Replies stored | thread T with `total_reply_count` 150, reply limit allows 150; page 1 = 100 + token, page 2 = 50 | two `comments.list` requests (`parentId`=T, the second with `maxResults=50`); 150 rows with `comment_level` `reply`, `parent_comment` T and the video of T; 150 run links; `total_replies_collected` 150 | No error expected |
| No replies | top-level comment with `total_reply_count` 0 | no `comments.list` request for it | No error expected |
| Limit | thread with 300 replies, limit 20 | one request with `maxResults=20`; 20 replies | No error expected |
| Known reply | reply already stored by an earlier run | row updated, `first_collected_at` kept, new link for this run | No error expected |
| Parent gone | `comments.list` 404 for thread T, other threads fine | T skipped; others stored; run `completed` | logged as a request-log row with its error |
| Failure midway | 403 `quotaExceeded` on the second thread | run `failed`; first thread's replies stored and linked; `total_replies_collected` = that count | existing handlers |
| Resume | a second run of the same query after the failure | all threads' replies present; no duplicate comment rows | No error expected |
| Token cycle | thread pages cycle A → B → A | stops after the cycle; no extra requests | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/collection.py` -- `_collect_replies(run, ...)` after `_collect_comments`, inside the same `try`. Reuse `_store_comment` by adding parameters for level and parent; reuse the token-set paging of `_collect_video_comments`, `_json_count` and the `finally` count pattern. Read the threads from `run.run_comments` filtered to `top_level` with `total_reply_count > 0`, in link order.
- `src/api/core/youtube_client.py` -- no change (`comments.list` cost 1, `parentId` redacted, `reasons` available). Detect the 404 by `exc.http_status == 404`.
- `src/api/core/models.py` -- no new table (the US-021 check constraint already allows replies with a parent). Add `SavedQuery.max_replies_per_comment` and `CollectionRun.requested_reply_limit`, and generate `0014`.
- `src/api/core/serializers.py`, `views.py` -- mirror `max_comments_per_video` exactly: the field, its validator and the copy in `CollectionRunStartView.post`. `CollectionRunSerializer` exposes `requested_reply_limit`. The collector reads `run.requested_reply_limit`.
- `src/ui/src/apiClient.ts`, `savedQueryForm.ts`, `App.tsx` and their tests -- mirror "Comments per video" with a "Replies per comment" input.
- `docs/database_schema.md` (thesis repo, separate docs commit) -- the two rows in Decisions.
- `src/api/core/tests.py` -- a `/comments` route in the `CollectRunTests` fake, a documented-shape `_reply_item` helper, one test per matrix row, and an end-to-end case through the real HTTP path.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/collection.py` -- the reply step, the 404 skip and the count.
- [x] `src/api/core/models.py` + migration `0014`, `serializers.py`, `views.py` -- the reply limit and the copy at start.
- [x] `src/ui/src/apiClient.ts`, `savedQueryForm.ts`, `App.tsx` + tests -- the form field.
- [x] `docs/database_schema.md` -- the two rows.
- [x] `src/api/core/tests.py` -- one test per matrix row.

**Acceptance Criteria:**
- Given the failure-midway test, when `total_replies_collected` is written only on success, then the test fails.
- Given the resume test, when replies are created instead of updated, then the test fails on the unique constraint or the row count.
- Given the parent-gone test, when a 404 fails the run, then the test fails.

## Implementation Notes

- `_store_comment` gained a keyword-only `parent`; with it the item is read as a comments.list comment (no thread wrapper, `total_reply_count` null). The reply step is `_collect_replies` plus `_collect_thread_replies`, mirroring `_collect_comments` / `_collect_video_comments`.
- Threads with a null `total_reply_count` are treated like 0 and get no request.
- The UI also shows the reply limit in the saved-query list ("Replies"), next to "Comments". `requested_reply_limit` is in the API and admin, not the UI run type (as `requested_comment_limit`).
- Acceptance mutations confirmed: count moved out of `finally` fails the failure-midway test; `create` for replies fails the resume test (IntegrityError on PostgreSQL); raising on 404 fails the parent-gone test.
- Orchestrator check: backend 218 OK on PostgreSQL, migrations clean; UI 60 pass, build and lint clean. UI baseline `725325cf7d927893b28073ffd7b0645604c7a6d8`; thesis baseline `45ff88c95a93271014b456a8c5dff1bbb6a54691`.
- Review patches (pass 1) applied by the orchestrator: three comment/docstring corrections. Full suite 218 OK on PostgreSQL.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 4, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `collect_run` docstring line pasted to 143 chars | low | patch | Confirmed; reflowed to 88 by the orchestrator. |
| `CollectionRunComment.page_number` / `thread_position` comments describe only top-level threads | low | patch | Confirmed: replies store the comments.list page and the reply's position. Comments reworded by the orchestrator. |
| `_json_count` docstring names only commentThreads.list | low | patch | Confirmed: now also used for replies. Reworded by the orchestrator. |
| `effective_params` row in `docs/database_schema.md` overflows its column padding | low | reject | Cosmetic; no formatter checks the doc and realigning would rewrite the whole table. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass.

**Manual checks:**
- Collect a query with 2 videos, 20 comments per video and 10 replies per comment. `/admin/` shows replies with their parent, and the run's logs show `comments.list` rows only for threads that have replies.
