# 26 - Purge YouTube data after 30 days

Story: US-040, Purge YouTube data after 30 days.

Status note: this document describes the US-040 implementation **after** the code review of 2026-10-07 and the fixes that followed it.

## What this story added

A management command:

```bash
venv/bin/python manage.py purge_youtube_data           # delete
venv/bin/python manage.py purge_youtube_data --dry-run # only report
```

It deletes YouTube data that was fetched more than 30 days ago, keeps everything the researcher wrote and every record of how data was collected, and marks runs whose data is now gone.

## Why this matters

The YouTube API Services Developer Policies (III.E.4.d) allow data obtained through the API to be stored for **at most 30 days**. Until now nothing deleted it, so every dataset would eventually have broken the policy. The thesis is built around this rule: the reproducible unit is the documented **procedure** (saved query, effective parameters, request logs), not the YouTube data itself. This command is what makes that design real.

## Key concept: what goes and what stays

The cutoff is `now − 30 days`. A row exactly at the cutoff is kept; only strictly older rows go.

| deleted | judged by |
| :-- | :-- |
| `youtube_channels` | `last_fetched_at` |
| `youtube_videos` | `last_fetched_at` |
| `youtube_comments` (top-level and replies) | `last_fetched_at` |
| `video_statistics_snapshots` | `captured_at` |

Deleting a row also deletes what depends on it:

- a **video** takes its run links, its snapshots and its comments with it;
- a **comment** takes its replies and its run links with it;
- a **channel** does not take its videos. They stay, with an empty channel link (`SET_NULL`, page 18).

**Kept** are the research projects, saved queries, collection runs (every counter and the copied parameters unchanged) and request logs. These describe *how* data was collected and contain no YouTube data (pages 12 and 24 show why the logs are safe to keep).

`last_fetched_at` is refreshed whenever a run fetches the data again (pages 17, 18 and 22). So data that keeps being re-collected stays; only data nobody has refreshed for 30 days is removed.

## Key concept: marking a run as purged

`collection_runs.data_purged_at` (added in US-010) records when a run's data was purged. A run is marked when the purge removes its **last** link to a video or comment, meaning all of that run's YouTube data is gone. That is exactly when the discovery summary (page 19) switches from the video list to "Data purged on <date>".

A run is **not** marked when:

- it still has a link, for example because a later run refreshed one of its videos;
- it never found anything;
- it was already marked.

## Key concept: one transaction, and a safe dry run

All deletes and all run marks happen inside one `transaction.atomic()`. If anything fails midway, PostgreSQL undoes the whole purge, and nothing is half-deleted.

`--dry-run` uses the same code: it runs the real purge, prints the counts, then **rolls the transaction back**. Its numbers are therefore exact, the same code path a real purge takes. The trade-off is that a dry run briefly locks the same rows a real purge would; a `ponytail:` comment in `purge.py` marks it.

## Key concept: do not purge while collecting

The cascades above are done by **Django**, not by the database. Django first finds the old rows, then deletes them by ID, without looking at their dates again. If `collect_runs` refreshes one of those videos in between, the purge still deletes it. Or, if the collector has just linked it to a new run, the purge fails at commit and rolls back completely.

Neither outcome corrupts anything, but the first loses fresh data. The rule is simple: **do not run `purge_youtube_data` while `collect_runs` is running.** Run the purge on its own, at least once a day. commands.md says the same.

## File-by-file explanation

### `src/api/core/purge.py`

- `RETENTION_DAYS = 30`: the policy limit. It is a constant, not an option, because it is policy, not configuration.

- `purge_youtube_data(now=..., dry_run=...)` returns a `PurgeResult`: the number of deleted rows per kind (cascades included) and the number of runs marked. It takes `now` as an argument so tests can pin the time.

### `src/api/core/management/commands/purge_youtube_data.py`

A thin command: it parses `--dry-run`, calls the function with the current time, and prints one line per kind, for example `core.YouTubeVideo: deleted 3`, then `core.CollectionRun: stamped 1` (`would delete` / `would stamp` in a dry run).

### `src/api/core/tests.py`

`PurgeYouTubeDataTests` sets time fields with `update()` to make rows old or fresh. It covers:

- an old video and everything it takes along
- a fresh video
- the exact boundary
- an old channel with a fresh video
- an old snapshot on a fresh video
- an old comment with a fresh reply
- run marking: fully purged, partly kept, never linked or already marked, and a run whose only link is a comment
- a dry run
- nothing old
- the command's output

A shared helper checks that exactly the same runs and request logs exist afterwards, with all seven counters unchanged. The review made this helper stricter: before, it would have passed even if the runs had been deleted.

## How the pieces connect

```text
manage.py purge_youtube_data [--dry-run]
   '-- purge_youtube_data(now, dry_run)
          cutoff = now - 30 days
          transaction.atomic():
             remember runs that have links and no data_purged_at
             DELETE channels   last_fetched_at < cutoff   (videos keep channel = null)
             DELETE videos     last_fetched_at < cutoff   (+ links, snapshots, comments, replies)
             DELETE comments   last_fetched_at < cutoff   (+ replies, links)
             DELETE snapshots  captured_at     < cutoff
             mark remembered runs that now have no links: data_purged_at = now
             dry run? -> roll everything back
          print counts
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py test core.tests.PurgeYouTubeDataTests
```

Passing looks like `OK` (240 tests). The second command runs only the purge tests. The command itself is described in [commands.md](commands.md), under 30-day purge.

## How to test manually

1. Bring your database up to date. `./run-local.sh` migrates SQLite on start. With Compose PostgreSQL, run `DATABASE_ENGINE=postgresql venv/bin/python manage.py migrate` from `src/api`.

2. Run `venv/bin/python manage.py purge_youtube_data --dry-run`. It prints zero or more counts and changes nothing.

3. Age one video in the Django shell (`venv/bin/python manage.py shell`):

   ```python
   from datetime import timedelta
   from django.utils import timezone
   from core.models import YouTubeVideo
   v = YouTubeVideo.objects.first()
   YouTubeVideo.objects.filter(pk=v.pk).update(last_fetched_at=timezone.now() - timedelta(days=31))
   ```

4. Run `venv/bin/python manage.py purge_youtube_data`. It reports `core.YouTubeVideo: deleted 1` and whatever went with it.

5. In `/admin/`: the video, its run links, snapshots and comments are gone, while the runs and their request logs remain. If that video was a run's only link, the run now shows **Data purged at**, and the UI's run detail says "Data purged on <date>" (page 19).

## Common errors

- **`relation "youtube_videos" does not exist`** (or another missing table). The database is behind on migrations. See step 1.

- **The purge deleted 0 rows but you expected some.** Nothing is older than 30 days. Re-collecting refreshes `last_fetched_at`, which resets the clock.

- **A run is not marked though some of its videos were purged.** It still has a link to a video another run refreshed. Only runs whose data is completely gone are marked.

## Known gaps

- Nothing schedules the command. Run it daily yourself, or with an operating-system scheduler such as `cron`.

- There is no lock between the purge and `collect_runs`. The operating rule above covers it.

- Processed data (cleaning in US-024, sentiment in US-025) does not exist yet. Those stories extend this command when they add tables holding derived YouTube data.
