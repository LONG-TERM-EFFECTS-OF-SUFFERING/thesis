---
title: 'Link collection runs to videos idempotently'
type: 'chore'
ticket: '4'
created: '2026-10-07'
status: 'built'
baseline_revision: '665ab11205f8ac49a10f262da1b38cd704632521'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** US-020 asks that repeated runs link videos without duplicates and that re-collecting refreshes a video's payload and fetch time. The behavior already exists:
- `youtube_videos.youtube_video_id` is unique, and videos and channels are written with `update_or_create`.
- `collection_run_videos` is unique per (run, video), with an in-run `seen` set.
- US-017 refreshes `raw_payload` and `last_fetched_at`.

Two proofs are missing, though: no test shows the database rejects a duplicate run-video link, and no test runs the **same query twice** through the real path and checks the whole dataset afterwards.

**Approach:** Add tests only. One is a model test for the `unique_collection_run_video` constraint. The other is an end-to-end test that runs `manage.py collect_runs` for two runs of the same saved query, with only `urllib.request.urlopen` stubbed. Run 2 serves the same video IDs with changed titles and counts. Afterwards the test asserts the dataset is linked without duplicates and refreshed.

## Boundaries & Constraints

**Always:**
- Tests live in `src/api/core/tests.py`, reusing the end-to-end helpers and fixtures of `CollectRunsEndToEndTests` (`serve_search`-style token routing, `_FakeHttpResponse`, `YOUTUBE_*_RESPONSE`).
- The fake must raise on any unexpected request, so a regression fails instead of hanging (US-034 rule).
- Each new assertion must fail when the behavior it covers is removed. Check by mutation once and record it in Implementation Notes.
- No test reaches `googleapis.com`. Validated on Compose PostgreSQL.

**Never:**
- No product code changes. If a test exposes a defect, stop and report it.
- No new models, migrations or dependencies.
- No moving or splitting existing tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Duplicate link | create a second `CollectionRunVideo` for the same run and video | rejected | `IntegrityError` |
| Same video, two runs | one video linked to run A and to run B | allowed: two links | No error expected |
| Repeated collection | the same query started and collected twice (run 2 serves the same video IDs, new titles and counts) | both runs `completed`. `youtube_videos` holds exactly one row per distinct video ID. Each run has one link per video. `youtube_channels` holds one row per channel. Each video has two statistics snapshots, one per run | No error expected |
| Refresh | after run 2 | every video's `title`, `raw_payload` and `last_fetched_at` come from run 2 (`last_fetched_at` later than after run 1); each channel's counts and `raw_payload` come from run 2; run 1's links and snapshots unchanged | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/tests.py` `CollectRunsEndToEndTests` -- holds the `urlopen` stub pattern, the `collect` helper, `_SentRequest`/`_UrlOpen`, and the fixtures `YOUTUBE_SEARCH_RESPONSE`, `YOUTUBE_SEARCH_LAST_PAGE`, `YOUTUBE_VIDEOS_RESPONSE` and `YOUTUBE_CHANNELS_RESPONSE`. Build run 2's responses with `copy.deepcopy` of those fixtures, changing the titles and counts.
- The model tests that already exist (e.g. `ApiRequestLogModelTests`, `VideoStatisticsSnapshotModelTests`) show the `IntegrityError` + `transaction.atomic()` pattern. Add `CollectionRunVideoModelTests` beside them.
- Two runs of one saved query: create the saved query, call the start endpoint (or `CollectionRun.objects.create` with the same `effective_params`) twice, and run `collect_runs` between the two starts so each call collects exactly one pending run.
- Do not touch `core/collection.py`, `core/youtube_client.py`, models or migrations.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/tests.py` -- `CollectionRunVideoModelTests` (duplicate rejected, same video in two runs allowed).
- [x] `src/api/core/tests.py` -- a repeated-collection end-to-end test covering the Repeated collection and Refresh rows.

**Acceptance Criteria:**
- Given the repeated-collection test, when `_store_video` creates a new `YouTubeVideo` instead of updating (for example `create` in place of `update_or_create`), then the test fails.
- Given the repeated-collection test, when `_store_details` stops refreshing `last_fetched_at` or `raw_payload`, then the test fails.
- `git diff --stat 665ab11 -- core/ ':!core/tests.py'` is empty.

## Implementation Notes

- `CollectionRunVideoModelTests` sits after `VideoStatisticsSnapshotModelTests`; `test_repeated_collection_links_once_per_run_and_refreshes` is the last test of `CollectRunsEndToEndTests`. It reuses `self.run` as run 1 (attached to a new saved query), then creates run 2 with the same `effective_params` and resets `self.served` between the two `collect_runs` calls.
- `serve` now reads `self.videos_response` / `self.channels_response` (set in `setUp` to the module fixtures) so run 2 can serve deep-copied fixtures with `Updated <id>` titles, `viewCount + 500` and `subscriberCount` 1300. Existing tests are unaffected.
- `_store_video` also writes `last_fetched_at` at search time, so "later than run 1" alone cannot catch a `_store_details` regression. The test also asserts `last_fetched_at >= ` run 2's `videos.list` log `finished_at`.
- Mutation check, Compose PostgreSQL, each reverted afterwards:
  - `_store_video` `update_or_create` -> `create`: ERROR (IntegrityError on `youtube_video_id`).
  - `_store_details` without the `last_fetched_at` line: FAIL (`last_fetched_at` earlier than the videos.list `finished_at`).
  - `_store_details` without the `raw_payload` line: FAIL (None != item).
  - `_store_details` keeping run 1's payload (`video.raw_payload or item`): FAIL.
  - `_store_channel` `update_or_create` -> `get_or_create`: FAIL (1200 != 1300).
  - `_store_channel` without `view_count` or without `video_count` (review fix: run 2 now changes all three channel counts): FAIL.
  - `unique_collection_run_video` removed through a throwaway migration: `test_one_link_per_run_and_video` FAILS (IntegrityError not raised).
- Orchestrator check: 189 OK on PostgreSQL; no stray migration; product diff empty. Thesis baseline `ed2ff9a8a0062bccb497dbf2aad1a420f719c56a`.
- Review patch (pass 1) applied: run 2 changes all three channel counts and the test asserts them. Full suite 189 OK on PostgreSQL; product diff empty.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 1, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Repeated-collection test changes only `subscriberCount`, so `view_count`/`video_count` refresh is unproven | low | patch | Confirmed: run 2's `viewCount` and `videoCount` equal run 1's; only `subscriber_count` asserted, short of the frozen Refresh row. Change both in the run-2 fixture and assert them. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && git diff --stat 665ab11 -- core/ ':!core/tests.py'` -- expected: empty.
