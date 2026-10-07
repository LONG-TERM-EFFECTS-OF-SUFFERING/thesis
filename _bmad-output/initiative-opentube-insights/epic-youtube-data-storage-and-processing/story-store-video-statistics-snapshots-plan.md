---
title: 'Store video statistics snapshots'
type: 'feature'
ticket: '3'
created: '2026-10-07'
status: 'built'
baseline_revision: 'd8ccc493e202e116f703a57f23134af1e29123a9'
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

**Problem:** View, like and comment counts change over time. Nothing records them, let alone what they were on each collection date, so engagement cannot be audited across runs (US-019).

**Approach:** The video details request asks for `statistics` too: `part=snippet,contentDetails,statistics`, which costs nothing extra. For each returned item that has a `statistics` object, the run stores one new `VideoStatisticsSnapshot` row with the video, the run, the parsed counts, `captured_at` and the raw `statistics` object. Snapshots are only added, never overwritten.

## Boundaries & Constraints

**Always:**
- **Table:** `VideoStatisticsSnapshot` (`video_statistics_snapshots`) matches `docs/database_schema.md`.
  - `video` is a `CASCADE` FK. `collection_run` is a `SET_NULL`, `null=True, blank=True` FK; the doc's `null: NO` on that row contradicts its own Django column, so follow the Django column.
  - The three counts are `PositiveBigIntegerField(null=True, blank=True)`. `captured_at` defaults to `timezone.now`, and `raw_statistics` is a nullable JSON field.
  - A `UniqueConstraint` on (`video`, `collection_run`) applies with `condition=Q(collection_run__isnull=False)`.
- **Counts:** `view_count`, `like_count` and `comment_count` come from `statistics.viewCount`, `likeCount` and `commentCount`. These are decimal strings, parsed with the existing `_count` (ASCII digits only; `bool`, negatives, non-digits and missing become null). Hidden likes or disabled comments arrive as missing keys, so they become null.
- **Raw data:** `raw_statistics` is the item's `statistics` object as sent.
- **When a snapshot is written:** only for videos updated from a `videos.list` item, and only when that item's `statistics` is an object. One snapshot per video per run. A later run adds a new snapshot; the earlier one is never changed.
- **Failure:** a failing `videos.list` call fails the run as today; snapshots from earlier batches stay.
- **Video row:** the video's own `raw_payload` now includes `statistics`, since it is the whole item. That is expected and needs no change.
- **Tests:** no test reaches `googleapis.com`. Validated on Compose PostgreSQL.

**Never:**
- No statistics columns on `youtube_videos`.
- No channel snapshots.
- No API endpoint or UI for snapshots: the admin is enough for this story.
- No purge (US-040 deletes by `captured_at`).
- No extra request: statistics ride on the existing `videos.list` call.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Snapshot stored | run collects 2 videos whose items carry `statistics` `{viewCount:"1500", likeCount:"30", commentCount:"4"}` | `videos.list` sent with `part=snippet,contentDetails,statistics`; 2 snapshots, each with the video, the run, 1500/30/4, `captured_at` set and `raw_statistics` equal to the object; request count and quota unchanged from US-018 | No error expected |
| Hidden counts | `statistics` without `likeCount` or `commentCount` | those counts null; `view_count` set | No error expected |
| Bad counts | `viewCount` `"-1"`, `"x"` or `true` | null | No error expected |
| No statistics | item without a `statistics` object, or a missing video | no snapshot for it; the video's details are still stored when the item exists | No error expected |
| Second run | the same video collected by a later run | a second snapshot with the new run and new counts; the first unchanged | No error expected |
| Constraint | two snapshots for the same video and run | rejected | `IntegrityError` |
| Run deleted | the snapshot's run is deleted | snapshot kept with `collection_run` null | No error expected |
| Failure | second `videos.list` batch fails | the run fails; first-batch snapshots kept | existing handlers |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` -- add `VideoStatisticsSnapshot` after `YouTubeVideo` (`related_name="statistics_snapshots"` on both FKs), in the house idioms. Generate `0012`.
- `src/api/core/collection.py`:
  - In `_collect_details`, change the `part` to `snippet,contentDetails,statistics`.
  - After `_store_details(video, item)` succeeds, call a new `_store_snapshot(video, run, item)`. It creates the row when `item["statistics"]` is a `Mapping`, reusing `_count`.
  - `_store_details`'s return value and the channel step stay as they are.
- `src/api/core/admin.py` -- register `VideoStatisticsSnapshot` with `ReadOnlyAdmin` (video, run, the three counts, `captured_at`), filtered by run.
- `src/api/core/tests.py`:
  - `_video_item` gains an optional `statistics` argument. Its docstring and the three `snippet,contentDetails` assertions (around lines 2564, 3143 and 3702) change to the new `part`.
  - Add one test per matrix row in `CollectRunTests` and a model test for the constraint and `SET_NULL`.
  - Add `statistics` to the end-to-end `YOUTUBE_VIDEOS_RESPONSE` and assert the snapshots.
- `docs/database_schema.md` (thesis repo, separate docs commit) -- correct `video_statistics_snapshots.collection_run_id` null to `YES`.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/models.py` + migration `0012` -- the snapshot model and the conditional unique constraint.
- [x] `src/api/core/collection.py` -- the `part` change and `_store_snapshot`.
- [x] `src/api/core/admin.py` -- read-only registration.
- [x] `src/api/core/tests.py` -- the matrix rows plus updated `part` assertions.
- [x] `docs/database_schema.md` -- the null fix.

**Acceptance Criteria:**
- Given the second-run test, when snapshots are updated in place instead of added, then the test fails.
- Given the bad-counts test, when `_count` is bypassed with plain `int()`, then the test fails.
- Given the end-to-end test (`urlopen` stubbed), when the run collects, then the `videos.list` URL carries `part=snippet,contentDetails,statistics` and the snapshots match `YOUTUBE_VIDEOS_RESPONSE`.

## Implementation Notes

- Migration is `0012_videostatisticssnapshot`. Snapshot `ordering` is (`video`, `captured_at`); `__str__` shows video id and capture minute.
- Beyond the matrix: a model test that run-less snapshots are not unique (the constraint's condition), and a 7-value bad-counts sweep mirroring the channel test.
- Mutation-checked: `update_or_create` in place, plain `int()`, the old `part`, and dropping the `_store_snapshot` call each fail tests.
- Orchestrator check: full suite 186 OK on PostgreSQL, migrations clean. Thesis baseline `f400abcecc34262dc5ac27b710d1174378313429`.
- Review patches (pass 1) applied: `_count` rejects values above `MAX_BIGINT`; docstring fixed. Full suite 186 OK on PostgreSQL.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 1, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `_count` accepts digit strings above the BIGINT ceiling; one oversized count raises `DataError` and fails the run | medium | patch | Confirmed: no upper bound; AGENTS.md range-check pitfall. Since every count (channels and snapshots) goes through `_count`, one bound closes it: `MAX_BIGINT = 2**63 - 1`, over → null; `str(2**63)` added to the bad-counts test, which fails with `DataError: bigint out of range` without the bound. Supersedes the US-018 rejection of the same class for channel counts. Applied by the orchestrator. |
| `_count` docstring summary has a spliced duplicate sentence and exceeds the line length | low | patch | Confirmed; direct correction. Applied by the orchestrator. |

## Design Notes

A snapshot is the run's reading of a moving number. Keeping one per video per run, never overwritten, is what lets a researcher see how engagement changed between collection dates within the 30-day window.

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.

**Manual checks:**
- Collect the same query twice (two runs, cap 5), then open `/admin/` → Video statistics snapshots. Each video has two snapshots, one per run, each with its own counts and `captured_at`.
