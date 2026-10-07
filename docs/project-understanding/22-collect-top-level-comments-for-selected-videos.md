# 22 - Collect top-level comments for selected videos

Story: US-021, Collect top-level comments for selected videos.

Status note: this document describes the US-021 implementation **after** the code review of 2026-10-07 and the fixes that followed it. It is the first story of the Comments and sentiment analysis epic.

## What this story added

Audience reaction lives in the comments. This story collects them:

- **A limit on the saved query.** The save form has a new optional field, **Comments per video**. Empty means "no comments" (the default, so quota use stays opt-in).

- **Two new tables.**
  - `youtube_comments` (`YouTubeComment`): one row per comment.
  - `collection_run_comments` (`CollectionRunComment`): which run fetched which comment, on which page and at which position.

- **A fourth step in each collection run**, after discovery, video details and channels:

```text
1. search.list         -> videos
2. videos.list         -> video details (and which videos still exist)
3. channels.list       -> channels
4. commentThreads.list -> top-level comments, up to N per video     <- new
```

Only **top-level** comments are collected here. Replies came with US-022 (page 23).

## Why this matters

The sentiment model (US-025) needs text to score, and the thesis needs to say exactly which comments were analyzed. Each comment is stored with its raw payload, a link to its video and to the run that fetched it, and `last_fetched_at`, which starts its 30-day retention window.

## Key concept: "selected videos" and the limit

Two decisions shaped this story:

- **Which videos are selected?** The videos the run collected details for **in this run**, the ones `videos.list` confirmed still exist. The saved query's criteria already chose them, so no separate selection screen is needed. A video deleted between search and details is skipped. Requesting its comments would fail with `404 videoNotFound`, and the code review caught exactly that.

- **Where does the limit live?** On the saved query, because it is part of the approved collection criteria. At **Start run** it is copied into the run, both into `effective_params` and into `requested_comment_limit`. So editing the query later never changes what an old run asked for. The limit means **up to N top-level comments per video**.

## Key concept: two quirks of the comments API

- **The original text is private.** YouTube returns `textOriginal` only to the comment's author. With an API key you normally get only `textDisplay`. So the app asks for `textFormat=plainText` and stores:
  - `text_display` = `textDisplay`
  - `text_original` = `textOriginal` if present, otherwise `textDisplay`. This is the text sentiment analysis will use.

- **Comments can be turned off.** For such a video `commentThreads.list` answers `403` with reason `commentsDisabled`. That is normal, not a failure: the video is skipped and the run continues. Any other error, such as `quotaExceeded`, still fails the run, and the comments stored before it stay. To tell the two apart cleanly, `YouTubeApiError` now carries YouTube's error **reasons** (`exc.reasons`), not just a message.

Counts in comments arrive as JSON numbers (`"likeCount": 12`), not as text like channel and video statistics. A separate helper, `_json_count`, accepts whole numbers only. It rejects `true`/`false` (the AGENTS.md `bool` pitfall) and values too large for the column.

## Key concept: paging that cannot run away

Each request returns up to 100 comment threads, and asks only for as many as are still needed (`maxResults = min(100, remaining)`). Paging stops when:

- the per-video limit is reached;
- YouTube sends no `nextPageToken`, or an empty page;
- YouTube sends a token **already used for this video**.

The last rule is stricter than the one on page 15. A set of every token sent catches a cycle like A → B → A, not only an immediate repeat. Without it, a cycle of already-known comments would never add a new link, and paging would continue until the quota ran out. The review caught this.

## Key concept: one comment row, many runs

`youtube_comment_id` is unique. When a later run fetches a known comment:

- the row is **updated**: likes, reply count, payload and `last_fetched_at`.
- `first_collected_at` is **kept**: it records when the app first saw the comment.
- the run gets its own link (one link per comment per run).

A database rule also guards the comment level: a `top_level` comment must have no parent, and a `reply` must have one. Replies arrive in US-022.

## File-by-file explanation

### `src/api/core/models.py` and `src/api/core/migrations/0013_youtubecomment_collectionruncomment_comment_limits.py`

- `YouTubeComment` and `CollectionRunComment`, with the level check and the unique link.
- `SavedQuery.max_comments_per_video` and `CollectionRun.requested_comment_limit`.

### `src/api/core/serializers.py` and `src/api/core/views.py`

- The saved query accepts `max_comments_per_video`, which must be at least 1, and `true` is rejected.
- `CollectionRunStartView` copies the limit into the new run.

### `src/api/core/youtube_client.py`

`YouTubeApiError.reasons`, parsed from YouTube's error body. The stored error message is unchanged (`HTTP 403: commentsDisabled`).

### `src/api/core/collection.py`

- `_collect_details` now also returns the videos it updated in this run.

- `_collect_comments` loops over those videos (skipping all of this when the limit is empty) and handles `commentsDisabled`.

- `_collect_video_comments` pages one video, and `_store_comment` maps one thread.

- `total_comments_collected` is written once, at the end.

### `src/api/core/admin.py`

Read-only pages for comments and run-comment links.

### `src/ui/src/apiClient.ts`, `src/ui/src/savedQueryForm.ts` and `src/ui/src/App.tsx`

- The "Comments per video" input, wired like "Videos" (`max_videos_to_discover`).
- The value on each saved-query card.
- A shared `optionalNumber` helper for both number fields.

### Tests

- **Backend** (`core/tests.py`):
  - one test per scenario: stored, text fallback, comments disabled, other errors, known comment, no limit, limit wiring, bad limit
  - a video missing from details
  - a token cycle
  - model tests for the level check and the unique link
  - an end-to-end test that sends a real `commentsDisabled` error body through the unfaked HTTP path

- **UI**: the form and API tests cover the new field. One test now proves a draft does not reset the researcher's limit (a review fix).

## How the pieces connect

```text
Saved query (max_comments_per_video = 20)
   '-- Start run --> CollectionRun.requested_comment_limit = 20, effective_params.max_comments_per_video = 20

collect_run(run)
   |-- _discover_videos
   |-- _collect_details   --> returns the videos updated in this run
   |-- _collect_channels
   '-- _collect_comments(run, those videos)          (limit empty -> nothing)
          for each video:
             commentThreads.list (videoId, plainText, time order, maxResults<=100, pageToken)
                commentsDisabled -> skip video
                other error      -> run failed
             _store_comment -> YouTubeComment (create or update) + CollectionRunComment
          total_comments_collected = links made in this run
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

Passing looks like `OK` (206 tests), `pass 60`, a finished build and no lint output.

## How to test manually

You need `YOUTUBE_API_KEY` in `src/api/.env`. With 2 videos and 20 comments each, a run costs about 105 units: one search page (100), plus single requests for video details, channels and each video's comments.

1. `cd src && ./run-local.sh`, then open the UI at `http://localhost:5173/`.

2. Save a query with **Videos** set to 2 and **Comments per video** set to 20. Click **Start run**.

3. In a second terminal: `cd src/api && venv/bin/python manage.py collect_runs`.

4. Click **Refresh** and open the run. The request logs end with `commentThreads.list` rows, one per video (or more if a video has many comments).

5. In `http://127.0.0.1:8000/admin/` → Youtube comments: up to 40 comments, each with its video, text and like count. Collection run comments links each one to the run.

## Common errors

- **A video has no comments, but the run completed.** Its comments are turned off. The run's request log shows `HTTP 403: commentsDisabled` for that video.

- **No `commentThreads.list` requests at all.** The saved query has no **Comments per video** value, or the run was started before you set it (the limit is copied at start).

- **Fewer comments than the limit.** The video simply has fewer top-level comments. Replies are not counted here.

## Known gaps

- Replies, and what happens to an interrupted run, came with US-022 (see page 23).

- A comment ID or author channel ID longer than 64 characters would fail the run. Real YouTube IDs are much shorter, the same as for videos and channels.

- Comments are not shown in the app yet. They are visible in the admin.
