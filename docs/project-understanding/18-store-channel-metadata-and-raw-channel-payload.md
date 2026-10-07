# 18 - Store channel metadata and raw channel payload

Story: US-018, Store channel metadata and raw channel payload.

Status note: this document describes the US-018 implementation **after** the code review of 2026-10-07 and the fix that followed it.

## What this story added

After US-017 a video knew its own details but not who published it. This story adds the channel:

- a new table, `youtube_channels` (model `YouTubeChannel`).

- a link from each video to its channel: `YouTubeVideo.channel`.

- a third step in every collection run, after discovery and video details:

```text
1. search.list   -> which videos match the query
2. videos.list   -> each video's details (and its channelId)
3. channels.list -> each channel's details             <- new
```

For each channel YouTube returns, the app stores:

| column | from the `channels.list` item |
| :-- | :-- |
| `youtube_channel_id` | `id` (unique) |
| `title`, `description` | `snippet` |
| `country_code` | `snippet.country` |
| `youtube_published_at` | `snippet.publishedAt` (when the channel was created) |
| `subscriber_count`, `video_count`, `view_count` | `statistics` |
| `raw_payload` | the whole item, exactly as YouTube sent it |
| `last_fetched_at` | now, which starts the 30-day retention window |

## Why this matters

A video's reach and tone depend on who published it. Channel size, country and age give the source context the thesis analysis needs, for example to tell a large news channel from a small personal one. As with videos, the raw payload is kept so any column can be checked against what YouTube actually sent, within the 30-day window.

## Key concept: where the channel ID comes from

The channel ID is taken from the **`videos.list`** item (`snippet.channelId`), not from the search result. That has two consequences:

- only videos that still exist get a channel. A video missing from `videos.list` (deleted or private) is never linked.

- each distinct channel is requested **once per run**, even if 20 of the run's videos come from it. Up to 50 channel IDs go in one request, at 1 quota unit each.

## Key concept: one row per channel, updated in place

`youtube_channel_id` is unique. When a later run meets a channel that is already stored, the row is **updated** (title, counts, payload, fetch time) with `update_or_create`, never duplicated. Many videos and many runs can point at the same channel row.

The counts on the row are overwritten each time: the table holds the **latest** values. Keeping dated history is a different pattern (snapshots), which US-019 adds for video statistics.

## Key concept: counts arrive as text

YouTube sends channel statistics as strings: `"subscriberCount": "1200"`. `_count` turns them into numbers carefully:

| YouTube sends | stored |
| :-- | :-- |
| `"1200"`, `"0"` | `1200`, `0` |
| nothing (for example `hiddenSubscriberCount: true`) | empty |
| `"-5"`, `"abc"`, `"١٢"` (non-ASCII digits) | empty |
| `true`, or a bare number `7` | empty |
| a number too large for the column (above 9,223,372,036,854,775,807) | empty (added in US-019, see page 20) |

The `true` case is the AGENTS.md pitfall: in Python `isinstance(True, int)` is `True`, so a careless check would store `true` as `1`. `_count` rejects `bool` explicitly and accepts only strings of ASCII digits.

## Key concept: links follow the latest data

A link is not only added, it can also be **removed**. When a video that was linked by an earlier run is collected again and:

- its channel no longer comes back from `channels.list` (for example, a terminated channel), or

- its `videos.list` item no longer names a channel,

then its `channel` is set back to empty. Without this, the video would keep pointing at stale data. The code review caught it. Each batch only clears its own videos, so if a later batch fails, the links already made stay.

## File-by-file explanation

### `src/api/core/models.py` and `src/api/core/migrations/0010_youtubechannel_youtubevideo_channel.py`

- `YouTubeChannel`, with the columns of `docs/database_schema.md`. The three counts are `PositiveBigIntegerField`, so PostgreSQL itself refuses negative values.

- `YouTubeVideo.channel`, a `ForeignKey` with `SET_NULL`: if a channel row is deleted (for example by the 30-day purge, US-040), its videos stay and only lose the link.

### `src/api/core/collection.py`

- `_store_details` now also returns the video's `snippet.channelId`, and clears the video's channel when that ID is missing.

- `_collect_channels(run, video_channels, ...)`:
  - groups the videos by channel and requests the channels in batches of 50
  - stores each returned channel
  - links its videos with one `UPDATE` per channel
  - unlinks videos whose channel did not come back

- `_store_channel(channel_id, item)` and `_count(value)`: the mapping and the number conversion described above.

`collect_run` calls `_collect_channels` right after `_collect_details`, inside the same error handling. A failing `channels.list` call therefore fails the run, and everything stored before it stays.

### `src/api/core/admin.py`

A read-only Youtube channels page, and a channel column on the video list.

### `src/api/core/tests.py`

- The fake transport gains a `/channels` route and a `_channel_item` helper.

- New tests cover:
  - channels stored and linked
  - batches of 50 + 10
  - count parsing and bad counts
  - a known channel updated, not duplicated
  - a missing channel
  - no videos collected (no request)
  - a failure
  - two re-collection cases that clear old links

- The end-to-end test (only `urlopen` faked) checks that a GET to `https://www.googleapis.com/youtube/v3/channels` with `part=snippet,statistics` follows the `videos.list` request.

### `docs/database_schema.md`

The `youtube_videos.channel_id` row said not-null while its own Django field says `null=True`. It now says nullable, matching the code. This is the same kind of fix as US-010's.

## How the pieces connect

```text
collect_run(run)
   |-- _discover_videos    search.list   -> videos + run links
   |-- _collect_details    videos.list   -> video details; returns {video: channelId}
   '-- _collect_channels   channels.list (distinct channel IDs, 50 per request)
          |-- _store_channel  -> YouTubeChannel (create or update)
          |-- UPDATE youtube_videos SET channel = <channel> WHERE id IN (...)
          '-- unreturned channel IDs -> UPDATE ... SET channel = NULL

YouTubeChannel 1 ----< YouTubeVideo >---- CollectionRunVideo ---- CollectionRun
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py makemigrations --check --dry-run
```

Passing looks like `OK` (170 tests) and `No changes detected`.

How to run a collection and reach the admin is in [commands.md](commands.md).

## How to test manually

You need a real `YOUTUBE_API_KEY` in `src/api/.env`. A run with a cap of 5 costs 102 units: one search page, one details request and one channels request.

1. `cd src && ./run-local.sh`, then open the UI at `http://localhost:5173/`.

2. Save a query with **Videos** set to 5 and click **Start run**.

3. In a second terminal: `cd src/api && venv/bin/python manage.py collect_runs`.

4. Click **Refresh** and open the run. The logs show `search.list`, `videos.list` and `channels.list`, in that order.

5. Open `http://127.0.0.1:8000/admin/` → Youtube channels. Each channel has counts and a `raw_payload`. Youtube videos now shows each video's channel.

## Common errors

- **`403: CSRF Failed: Origin checking failed - http://127.0.0.1:5173 ...`** when creating or saving in the UI. You are logged into `/admin/` on the same host name. Open the UI as `http://localhost:5173/` instead (see page 11 and commands.md). This is not caused by this story.

- **A channel has an empty subscriber count.** The channel hides its subscriber count, so YouTube does not send it. This is expected.

- **A video has no channel.** Either it was not collected (missing from `videos.list`), or YouTube did not return its channel. Check the run's `channels.list` log row.

## Known gaps

- An over-long country or channel ID would fail the run on PostgreSQL. Real YouTube data does not do this, and the review left it, as in US-015 and US-017. (Oversized counts used to be in this list; US-019 fixed them for every count, see page 20.)

- Channel counts keep only the latest value. Dated history of statistics is US-019, for videos.
