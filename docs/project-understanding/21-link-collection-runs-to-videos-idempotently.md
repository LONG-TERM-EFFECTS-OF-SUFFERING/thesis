# 21 - Link collection runs to videos idempotently

Story: US-020, Link collection runs to videos idempotently.

Status note: this document describes the US-020 implementation **after** the code review of 2026-10-07 and the fix that followed it. Like US-034 (page 15), this story added **tests only**: the behavior it asks for was already built by earlier stories, and this story proves it.

## What this story added

US-020 asks two things of repeated collection:

1. running a query again must not duplicate videos or run-video links.

2. collecting a video again must refresh its payload and fetch time.

Both were already true, so the story first **audited** the code and then added the two missing proofs:

- `CollectionRunVideoModelTests`: the database itself refuses a second link of the same video to the same run, and allows the same video to be linked to two different runs.

- `test_repeated_collection_links_once_per_run_and_refreshes`: the same saved query is collected **twice**, end to end, and the whole dataset is checked afterwards.

## Why this matters

A research dataset is often collected more than once: to follow a topic over time, or after a failed run. If each run copied every video, counts and analysis would double without anyone noticing. If re-collecting did not refresh the data, the 30-day clock and the stored values would be stale. The thesis needs evidence that neither happens, and a single test that walks through two real runs gives that evidence in one place.

## Key concept: idempotent

An operation is **idempotent** when doing it again leaves the data as if it had been done once, apart from the parts that are *meant* to change. Here:

| doing a second run | stays single | changes on purpose |
| :-- | :-- | :-- |
| videos | one `youtube_videos` row per YouTube video ID | title, `raw_payload`, `last_fetched_at` refreshed |
| channels | one `youtube_channels` row per channel | counts, `raw_payload`, `last_fetched_at` refreshed |
| run-video links | one link per video **per run** | the new run gets its own links |
| statistics | | a new snapshot per video for the new run (US-019) |

## Key concept: where the guarantee comes from

Several earlier pieces, at two levels, add up to the guarantee:

- **The database refuses duplicates.**
  - `youtube_video_id` and `youtube_channel_id` are unique.
  - A (run, video) link is unique.
  - A (video, run) snapshot is unique.

- **The code updates instead of creating.**
  - Videos and channels are written with `update_or_create`.
  - Within one run, the collector's `seen` set skips a video it already linked (US-015).

The database rules are the safety net. If the code ever tried to create a duplicate, PostgreSQL would refuse it, instead of silently storing two rows.

## Key concept: a test that proves the right thing

Two details make the end-to-end test trustworthy:

- **Run 2 sends different data**: new titles, new view counts and new values for all three channel counts. If run 2 sent the same data as run 1, a broken refresh would leave identical values, and the test could not tell. The review caught exactly this for two channel counts, which had been left the same.

- **The fetch time is checked against the details request.** The search step also writes `last_fetched_at`, so "later than after run 1" alone would not prove the *details* step refreshed it. The test checks that `last_fetched_at` is no earlier than the moment run 2's `videos.list` request finished.

The implementer also broke the code on purpose to confirm the tests catch it, then restored it:

- creating videos instead of updating them
- dropping the payload refresh
- dropping the fetch-time refresh
- not refreshing channels
- removing the link rule

Each one made a test fail.

## File-by-file explanation

### `src/api/core/tests.py`

- `CollectionRunVideoModelTests`: the two database tests above.

- `CollectRunsEndToEndTests.serve` now reads the `videos.list` and `channels.list` responses from the test instance, so one test can serve run 1 and run 2 different data. The existing tests are unaffected.

- `test_repeated_collection_links_once_per_run_and_refreshes`: the two-run test. Only `urllib.request.urlopen` is faked, so the real request, logging, storage and command code all run.

No product file changed.

## How the pieces connect

```text
saved query
   |-- run 1: collect_runs --> 5 videos, 1 channel, 5 links (run 1), 5 snapshots (run 1)
   '-- run 2: collect_runs --> same 5 video rows (updated)
                               same 1 channel row (updated)
                               5 new links (run 2)          run 1's links untouched
                               5 new snapshots (run 2)      run 1's snapshots untouched
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py test core.tests.CollectRunsEndToEndTests core.tests.CollectionRunVideoModelTests
```

Passing looks like `OK` (189 tests). The second command runs only the tests this story touched.

## How to test manually

The page 20 recipe does it with a real key: collect the same query twice with a cap of 5. Then in `/admin/`:

- **Youtube videos** has no duplicate IDs. Each video's `last_fetched_at` is from the second run.

- **Collection run videos** has 5 links for each run.

- **Video statistics snapshots** has two per video.

## Common errors

- **`IntegrityError` mentioning `unique_collection_run_video`.** Something tried to link a video to the same run twice. The collector never does this: its `seen` set prevents it. So check any new code that creates links.

- **A video appears twice in the admin with the same title.** Look at the YouTube IDs: two different videos can share a title. The same ID never appears twice.

## Known gaps

- None found by the audit. Two collections running **at the same time** on the same new video are handled by `update_or_create`, which retries when the other run inserts first, but no test exercises real concurrency.
