# 17 - Store video metadata and raw video payload

Story: US-017, Store video metadata and raw video payload.

Status note: this document describes the US-017 implementation **after** the code review of 2026-10-07 and the fixes that followed it.

## What this story added

Discovery (US-015) stores only what a search result contains: a video ID, a title, a shortened description and a publish date. That is enough to know *which* videos a query found, but not enough to analyze them. This story adds a second step to every collection run:

1. **Discover**, as before: `search.list` pages until the cap.

2. **Collect details**, new: `videos.list` for the run's videos, up to 50 IDs per request.

For each video YouTube returns, the app now stores:

| column | from the `videos.list` item |
| :-- | :-- |
| `title`, `description` | `snippet` (the **full** description replaces the shortened search one) |
| `youtube_published_at`, `live_broadcast_content` | `snippet` |
| `tags` | `snippet.tags` (a list of strings; `[]` when absent) |
| `category_id`, `default_language`, `default_audio_language` | `snippet` |
| `duration_iso8601` | `contentDetails.duration`, e.g. `PT4M13S` |
| `resolution` | `contentDetails.definition`, `hd` or `sd` |
| `caption_status` | `contentDetails.caption`, `"true"` or `"false"` |
| `raw_payload` | the whole item, exactly as YouTube sent it |
| `last_fetched_at` | now, which restarts the 30-day retention window |

The run counts these videos in `total_videos_collected` (US-012 added the column; this story fills it).

## Why this matters

The thesis analysis needs more than titles: duration, definition, captions, tags and categories describe the dataset. Keeping the **raw payload** next to the cleaned columns means any value can be checked against exactly what YouTube said, for as long as the data may be kept. Refreshing `last_fetched_at` keeps the 30-day purge (US-040) honest: the clock starts at the most recent fetch.

## Key concept: two calls, two prices

| call | what it returns | quota cost |
| :-- | :-- | :-- |
| `search.list` | up to 50 search results per page | 100 per page |
| `videos.list` | full details for up to 50 videos per request | 1 per request |

Details are almost free next to search, so they run as part of every collection rather than as a separate command. A run with a cap of 60 costs 2 search pages (200) plus 2 detail requests (2), 202 units in total.

Only `part=snippet,contentDetails` is requested. `statistics` (views, likes, comments) would cost nothing extra, but it belongs to US-019, which stores statistics as dated snapshots instead of overwriting them.

## Key concept: store what YouTube sent, narrowly

The detail item comes from outside, so it is narrowed field by field, the same way `_store_video` handles search results:

- a field that is missing, or has the wrong type, becomes empty (`null`, or `[]` for tags). The rest of the item is still stored.

- tags keep only text entries. A list like `["movilidad", 7, "Cali"]` is stored as `["movilidad", "Cali"]` (a review fix).

- otherwise values are stored **as YouTube sends them**, with no cleaning. Cleaning and normalization are US-024.

A discovered video that is missing from the `videos.list` response (deleted or made private since the search) keeps its search data, has no `raw_payload`, and is not counted as collected.

## Key concept: failure keeps what was done

If a `videos.list` request fails (for example `HTTP 403: quotaExceeded`), the run ends `failed` through the same handlers as a search failure. Everything stored before the failure stays: the discovered links, and the details from earlier batches. `total_videos_collected` is written in a `finally` block, so it is correct even after a failure.

## File-by-file explanation

### `src/api/core/models.py` and `src/api/core/migrations/0009_youtubevideo_details.py`

The eight new `YouTubeVideo` columns, with types matching `docs/database_schema.md`.

### `src/api/core/collection.py`

- `DETAILS_BATCH_SIZE = 50`: the most IDs `videos.list` accepts at once.

- `_collect_details(run, ...)`: reads the run's videos in discovery order, sends one `videos.list` request per 50 IDs through `call_youtube`, matches each returned item to its video by `item["id"]`, and writes `total_videos_collected`.

- `_store_details(video, item)`: the field mapping in the table above.

`collect_run` calls `_collect_details` right after `_discover_videos`.

### `src/api/core/admin.py`

The video list in `/admin/` now shows duration, definition and caption status, with filters on the last two.

### `src/api/core/tests.py`

- The fake transport in `CollectRunTests` now routes by URL path (`/search` versus `/videos`).

- New tests cover:
  - details stored after the search, with `raw_payload` compared against a fresh copy of the item
  - batches of 50 + 10
  - a video missing from the response
  - sparse and wrong-typed fields
  - re-collecting a known video
  - a run that discovers nothing (no `videos.list` call)
  - a failure on the second batch

- The end-to-end test (only `urlopen` faked) checks that a GET to `https://www.googleapis.com/youtube/v3/videos` follows the search requests, logged with `id` as `{"redacted_count": 5}`.

## How the pieces connect

```text
manage.py collect_runs
   '-- collect_run(run)
          |-- transition_to("running")
          |-- _discover_videos   search.list pages   -> YouTubeVideo + CollectionRunVideo
          |-- _collect_details   videos.list x ceil(n/50)
          |      |-- call_youtube(run, "videos.list", {part, id=a,b,c...})
          |      |      -> ApiRequestLog (id logged as a count), run totals +1 request / +1 quota
          |      '-- _store_details(video, item) -> metadata, raw_payload, last_fetched_at
          |      total_videos_collected = videos updated
          '-- transition_to("completed")  or  ("failed", error_message=...)
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py makemigrations --check --dry-run
```

Passing looks like `OK` (160 tests) and `No changes detected`.

How to run a collection and how to reach the admin are in [commands.md](commands.md), under Collection runs and Django admin.

## How to test manually

This spends a little real quota (101 units for a cap of 5), so you need `YOUTUBE_API_KEY` in `src/api/.env`.

1. Start the app: `cd src && ./run-local.sh`. Open the UI at `http://localhost:5173/`.

2. Save a query with **Videos** set to 5, then click **Start run**.

3. In a second terminal: `cd src/api && venv/bin/python manage.py collect_runs`. It prints `<run id>: completed, 5 videos`.

4. Click **Refresh** in the Collection runs panel and open the run. It shows one `search.list` row and one `videos.list` row.

5. Open `http://127.0.0.1:8000/admin/` → Youtube videos → any video. Duration, definition, caption status, tags and `raw_payload` are filled, and the description is the full text.

## Common errors

- **A video has a title but no duration or `raw_payload`.** It was discovered, but `videos.list` did not return it: it was deleted or made private in between. This is expected and not counted as collected.

- **The run ends `failed` with `HTTP 403: quotaExceeded` after the search succeeded.** The details request hit the quota limit. Discovered videos and earlier batches are kept.

- **The run stays `pending`.** Collection only happens when you run `collect_runs` (see commands.md).

## Known gaps

- Values are stored without length checks. An unexpectedly long value, or an impossible publish date, would fail the run on PostgreSQL. Real YouTube data does not do this, and the review left it.

- No statistics yet (US-019), no channel data or channel link yet (US-018), and no cleaning yet (US-024).
