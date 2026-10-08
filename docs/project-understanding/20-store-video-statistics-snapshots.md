# 20 - Store video statistics snapshots

Story: US-019, Store video statistics snapshots.

Status note: this document describes the US-019 implementation **after** the code review of 2026-10-07 and the fixes that followed it.

## What this story added

A video's view, like and comment counts change every day. This story records **what they were when each run collected the video**:

- a new table, `video_statistics_snapshots` (model `VideoStatisticsSnapshot`).

- the video details request (US-017) now also asks YouTube for `statistics`.

- for each collected video, the run adds one snapshot row:

| column | meaning |
| :-- | :-- |
| `video` | the video the counts belong to |
| `collection_run` | the run that read them (emptied, not deleted, if the run is deleted) |
| `view_count`, `like_count`, `comment_count` | the counts at that moment (empty when hidden or unreadable) |
| `captured_at` | when they were read |
| `raw_statistics` | the `statistics` object exactly as YouTube sent it |

## Why this matters

The thesis analysis works with engagement. A single "current" number cannot say whether a video gained views between two collections, or what its numbers were on the date a dataset was built. Snapshots keep one dated reading per video per run, so a researcher can audit the numbers behind any run and compare runs, within the 30-day window YouTube allows.

## Key concept: a snapshot is added, never overwritten

Compare the two storage patterns used so far:

| | latest value (US-018 channels) | snapshots (this story) |
| :-- | :-- | :-- |
| a second run reads new numbers | the row is **updated** | a **new row** is added |
| the old numbers | lost | kept, with their date and run |

A unique rule allows only **one snapshot per video per run**: the same run cannot record a video twice. Snapshots with no run (after the run was deleted) are not covered by the rule, so they never conflict. It is a *conditional* unique constraint, a database rule that applies only to rows matching a condition (here, `collection_run` is set).

## Key concept: statistics come for free

Quota is charged **per request**, not per field. Adding `statistics` to the existing `videos.list` call (`part=snippet,contentDetails,statistics`) costs nothing extra: a run with a cap of 5 still costs 102 units. There is no new request.

## Key concept: counts that cannot break a run

YouTube sends counts as text (`"viewCount": "1500"`). All counts, for snapshots and for channels, go through one function, `_count`:

| YouTube sends | stored |
| :-- | :-- |
| `"1500"` | `1500` |
| missing (hidden likes, disabled comments) | empty |
| `"-1"`, `"x"`, `"1.5"`, `"١٢"` | empty |
| `true`, or a bare number `7` | empty |
| a number too large for the column (above 9,223,372,036,854,775,807) | empty |

The last row came from the code review. Without it, a single impossible number would make PostgreSQL refuse the row (`DataError: bigint out of range`) and fail the **whole run**. Because every count goes through `_count`, one bound (`MAX_BIGINT`) fixes it for channels too.

## File-by-file explanation

### `src/api/core/models.py` and `src/api/core/migrations/0012_videostatisticssnapshot.py`

`VideoStatisticsSnapshot`, with the conditional unique constraint. A video's snapshots are reachable as `video.statistics_snapshots`, and a run's as `run.statistics_snapshots`.

### `src/api/core/collection.py`

- `_collect_details` requests the `statistics` part.

- `_store_snapshot(video, run, item)` adds one snapshot after the video's details are stored, but only when the item has a `statistics` object.

- `_count` gained the upper bound, and `MAX_BIGINT` is defined at the top of the module.

### `src/api/core/admin.py`

A read-only Video statistics snapshots page, filterable by run.

### `src/api/core/tests.py`

- New tests cover:
  - snapshots stored
  - hidden counts
  - bad counts, including one too large for the column
  - items with no statistics
  - a second run adding a second snapshot
  - a deleted run
  - a failure partway through

- Model tests check the unique rule and the emptied run link.

- The end-to-end test checks the new `part` in the request URL and every stored snapshot.

### `docs/database_schema.md`

The snapshot's `collection_run_id` row said not-null while its Django field says `null=True`. It now says nullable, the same kind of fix as before.

## How the pieces connect

```text
_collect_details(run)
   videos.list  part=snippet,contentDetails,statistics   (one request per 50 videos)
   for each returned item:
      _store_details(video, item)        -> video columns, raw_payload   (US-017)
      _store_snapshot(video, run, item)  -> NEW VideoStatisticsSnapshot row
                                            counts via _count, raw_statistics

YouTubeVideo 1 ----< VideoStatisticsSnapshot >---- 0..1 CollectionRun
                      (one per video per run)
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py makemigrations --check --dry-run
```

Passing looks like `OK` (186 tests) and `No changes detected`.

## How to test manually

You need `YOUTUBE_API_KEY` in `src/api/.env`. Two runs with a cap of 5 cost about 204 units.

1. `cd src && ./run-local.sh`, then open the UI at `http://localhost:5173/`.

2. Save a query with **Videos** set to 5. Click **Start run**, then run `venv/bin/python manage.py collect_runs` from `src/api`.

3. Click **Start run** on the same query again, and run `collect_runs` again.

4. Open `http://127.0.0.1:8000/admin/` → Video statistics snapshots. Each video appears twice, once per run, each with its own counts and `captured_at`. The view counts may already differ.

## Common errors

- **A snapshot has an empty like or comment count.** The video hides its likes, or has comments turned off, so YouTube does not send that number. This is expected.

- **A video has no snapshot for a run.** That run did not collect the video's details: it was deleted or made private, or the run failed before that batch.

## Known gaps

- Snapshots are only visible in the admin. Showing them in the app (for example as a chart across runs) belongs to the results and visualization stories.

- The purge (US-040, page 26) deletes snapshots by `captured_at` after 30 days, like the rest of the YouTube data.
