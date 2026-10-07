# 19 - Show video discovery summary

Story: US-016, Show video discovery summary.

Status note: this document describes the US-016 implementation **after** the code review of 2026-10-07 and the fixes that followed it. With this story, every story of the Traceable YouTube collection epic (US-010 to US-016) is built.

## What this story added

Opening a run in the **Collection runs** panel (US-014) now shows two sections:

- **Discovery**: how many videos the run discovered, how many search results it skipped and how many it collected details for, followed by a numbered list of the discovered video IDs. Each ID links to the video on YouTube, with its title next to it.

- **Requests**: the request-log table from US-014, as before.

Behind it:

- a new stored counter on the run, `total_videos_skipped`.

- the run endpoints also return `total_videos_skipped` and `data_purged_at`.

- the run detail returns `discovered_videos`: each video's ID, title, search page and discovery time.

## Why this matters

A researcher should understand a collection at a glance. For example: "the query found 60 videos, 4 search results were skipped, and details came back for 58." The skipped count explains why the discovered count can be lower than the number of search results. The list lets anyone check exactly which videos make up the dataset.

## Key concept: what "skipped" means

`search.list` returns search **results**, and not every result becomes a new video for the run. A result is **skipped** when it adds nothing new:

- it is a repeat: the same video already appeared earlier in this run (YouTube's pages can overlap).

- it is not a video: search can return channels or playlists, which have no `videoId`.

Results the collector never looked at, because the cap was already reached, are **not** counted as skipped. The counter is written at the end of discovery in the same `finally` block as `total_videos_discovered`, so both are correct even if a later page fails.

US-015 deliberately left this counter for this story, because this is where it is shown.

## Key concept: counts that survive the purge

YouTube's policy allows video data to be kept for 30 days. The purge (US-040, not built yet) will then delete the `youtube_videos` rows, and with them the run-to-video links (`CASCADE`). The run row itself is kept as a methodological record, and its `data_purged_at` is set.

So the summary reads its numbers from the **run row**, never by counting the list:

| | before the purge | after the purge |
| :-- | :-- | :-- |
| discovered, skipped and collected counts | from the run row | still from the run row, unchanged |
| video list | the run's links | empty, replaced by "Data purged on <date>" |

A test proves this. It builds a run with counts set and no links, as a purged run would look, and checks that the API still returns the counts.

## File-by-file explanation

### `src/api/core/models.py` and `src/api/core/migrations/0011_collectionrun_total_videos_skipped.py`

`CollectionRun.total_videos_skipped`, a `PositiveIntegerField` that defaults to 0.

### `src/api/core/collection.py`

`_discover_videos` adds one to `skipped` wherever it already ignored a result (no video ID, or already seen), and writes it in the final `UPDATE`.

### `src/api/core/serializers.py` and `src/api/core/views.py`

- Both run serializers add `total_videos_skipped` and `data_purged_at`.

- `DiscoveredVideoSerializer` turns one run-video link into `{youtube_video_id, title, page_number, discovered_at}`.

- The run detail adds `discovered_videos`, in discovery order. The view loads the links and their videos in one extra query (`Prefetch` with `select_related`), not one query per video.

### `src/api/core/tests.py`

- A collector test: page 1 has `a`, `b` and a channel result, and page 2 has `b` and `c`. The run discovers 3 and skips 2.

- Further collector tests: results past the cap are not counted, and the count survives a failed page.

- API tests: the new fields are on the list and the detail, `discovered_videos` is in order, and a purged run still returns its counts.

- The shared `TOTAL_FIELDS` list now includes the new counter, so the model default and the start response check it too (a review fix).

### `src/ui/src/apiClient.ts`

`CollectionRun` gains `total_videos_skipped`, `total_videos_collected` and `data_purged_at`. A new `DiscoveredVideo` type has its own guard, and the run-detail guard requires a valid `discovered_videos` list.

### `src/ui/src/App.tsx` and `src/ui/src/App.css`

The run detail now has a heading naming the run, then the **Discovery** and **Requests** subheadings. Earlier the heading said "Requests for …" above the new summary; the review caught that, since screen readers navigate by heading. Links use `encodeURIComponent` on the ID and open in a new tab with `rel="noreferrer"`.

### `docs/database_schema.md`

A `total_videos_skipped` row in the `collection_runs` table.

## How the pieces connect

```text
_discover_videos (US-015)
   for each search result:
      no videoId      -> skipped += 1
      already in run  -> skipped += 1
      new video       -> link it
   finally: UPDATE run SET total_videos_discovered = ..., total_videos_skipped = ...

GET /api/projects/<p>/runs/<r>/
   run row: discovered, skipped, collected, data_purged_at
   discovered_videos: run links -> video ID, title, page, time   (empty after purge)
   request_logs (US-014)

Run detail in the UI
   <h3> query (status)
   <h4> Discovery: counts from the run row; ID list, or "Data purged on <date>"
   <h4> Requests:  the log table
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
cd ../ui
npm test
npm run build
npm run lint
```

Passing looks like `OK` (176 tests), `pass 60`, a finished build and no lint output.

## How to test manually

You need `YOUTUBE_API_KEY` in `src/api/.env`.

1. `cd src && ./run-local.sh`, then open the UI at `http://localhost:5173/`.

2. Save a query with **Videos** set to 5 and click **Start run**.

3. In a second terminal: `cd src/api && venv/bin/python manage.py collect_runs`.

4. Click **Refresh** and open the run. Under **Discovery**, the discovered count equals the number of listed IDs. Skipped is usually 0 or small.

5. Click an ID. The video opens on YouTube in a new tab.

The "Data purged on" message cannot be seen yet, because the purge (US-040) does not exist. The API test covers that case.

## Common errors

- **Discovered is lower than the number of search results.** The difference is the skipped count: repeats and non-video results.

- **Collected is lower than discovered.** Some discovered videos were deleted or made private before the details request (see page 17).

- **`403: CSRF Failed`** when starting a run. You are logged into `/admin/` on the same host name. Open the UI as `http://localhost:5173/` (see commands.md).

## Known gaps

- The list is not paginated. Even a large cap gives a few hundred IDs, which a plain list handles.

- The panel has no automated render test, so the manual check above is how the Discovery section itself is verified.
