# 23 - Collect comment replies with pagination and resume handling

Story: US-022, Collect comment replies with pagination and resume handling.

Status note: this document describes the US-022 implementation **after** the code review of 2026-10-07 and the fixes that followed it.

## What this story added

US-021 collected top-level comments only. A conversation under a comment (its **replies**) was lost. This story collects them:

- **A second limit on the saved query.** The save form has a new optional field, **Replies per comment**, next to **Comments per video**. Empty means "no replies", so the quota stays opt-in.

- **A fifth step in each collection run**, after top-level comments:

```text
1. search.list         -> videos
2. videos.list         -> video details
3. channels.list       -> channels
4. commentThreads.list -> top-level comments
5. comments.list       -> replies, up to N per top-level comment      <- new
```

- **Honest partial results.** If a run fails partway, it keeps and reports exactly what it stored. Collecting the same query again completes the data without duplicates.

No new table: a reply is a row in `youtube_comments` with `comment_level = reply` and `parent_comment` pointing at its top-level comment. US-021's database rule already required exactly that shape.

## Why this matters

Replies are where much of the debate happens: agreement, disagreement, answers. Sentiment analysis (US-025) and any reading of audience reaction need them. And because collection can be interrupted (quota runs out, the network drops), the thesis must be able to say exactly how much was collected, not "something went wrong".

## Key concept: which threads get a reply request

A reply request costs 1 quota unit, so the step asks only where it makes sense:

- only the top-level comments linked to **this run**.
- only those whose stored `total_reply_count` is greater than 0. YouTube already said how many replies each comment has, so asking about the rest would waste quota.

Each request uses `comments.list` with `parentId` = the top-level comment's YouTube ID, `textFormat=plainText` and up to 100 replies per page. `parentId` is a YouTube ID, so the request log stores only a count of it (US-013).

(`commentThreads.list` can also return replies, but at most 5 per thread. `comments.list` returns all of them, page by page.)

## Key concept: paging, again

Reply paging follows the same rules as top-level comments (page 22). It stops at:

- the per-comment reply limit;
- no `nextPageToken`, or an empty page;
- a page token **already sent for this thread**, so a cycle such as A → B → A cannot loop.

Each page asks only for the replies still needed: `maxResults = min(100, remaining)`.

## Key concept: "resume" without new machinery

The backlog asks that an interrupted collection can "resume or report partial collection safely". The chosen design does both, without storing any cursor:

1. **Report partial.** Every reply is saved and linked as soon as it arrives. The run's `total_replies_collected` is written in a `finally` block, so even a run that ends `failed` (for example on `HTTP 403: quotaExceeded`) shows the true number it stored, and its request logs show exactly which page failed.

2. **Resume by re-running.** A failed run stays `failed`; that status is final since US-010. To finish the job, start the same saved query again. The new run re-requests every thread. Comments and replies already stored are **updated, not duplicated** (`youtube_comment_id` is unique), and each keeps its `first_collected_at`. The new run gets its own links.

A true "continue this exact run" mode would have needed stored page tokens, a new command option and an exception to "failed is final". That was judged not worth it here.

## Key concept: a deleted parent is not a failure

Between the top-level step and the reply step, an author can delete their comment. `comments.list` then answers `404`. That thread is skipped, its request log row keeps the error, and the run continues, just as a video with comments turned off is skipped in US-021. Any other error still fails the run.

## File-by-file explanation

### `src/api/core/models.py` and `src/api/core/migrations/0014_collectionrun_requested_reply_limit_and_more.py`

- `SavedQuery.max_replies_per_comment` and `CollectionRun.requested_reply_limit`.

- The comments on `CollectionRunComment.page_number` and `thread_position` now say what they mean for replies too: the `comments.list` page of the parent thread, and the position on that page.

### `src/api/core/serializers.py` and `src/api/core/views.py`

- The new limit is validated like the comment limit: at least 1, and `true` is rejected.

- `CollectionRunStartView` copies it into the run's `effective_params` and `requested_reply_limit`.

### `src/api/core/collection.py`

- `_collect_replies(run, ...)` picks the threads, skips a `404`, and writes `total_replies_collected` in its `finally`.

- `_collect_thread_replies(run, parent, limit, ...)` pages one thread.

- `_store_comment(video, item, parent=...)` is the US-021 function, extended: given a parent, it stores the item as a reply.

### `src/api/core/admin.py`

The run page shows `requested_reply_limit`.

### `src/ui/src/apiClient.ts`, `src/ui/src/savedQueryForm.ts` and `src/ui/src/App.tsx`

- The **Replies per comment** input, wired like **Comments per video**.
- A "Replies" entry on each saved-query card.

### Tests

- **Backend** (`core/tests.py`):
  - one test per scenario: no limit, limit wiring, bad limit, replies stored over two pages, no replies, the limit, a known reply, a deleted parent, a failure midway, resume, a token cycle
  - an end-to-end test through the real HTTP path that fetches replies and skips a `404` parent

- **UI**: the form and API tests cover the new field.

## How the pieces connect

```text
Saved query (max_comments_per_video = 20, max_replies_per_comment = 10)
   '-- Start run --> requested_comment_limit = 20, requested_reply_limit = 10

collect_run(run)
   ... _collect_comments   --> top-level comments (US-021)
   '-- _collect_replies    (reply limit empty -> nothing)
          for each top-level comment of this run with total_reply_count > 0:
             comments.list (parentId, plainText, maxResults<=100, pageToken)
                404           -> skip this thread
                other error   -> run failed (replies so far kept)
             _store_comment(parent=...) -> reply row + CollectionRunComment
          finally: total_replies_collected = reply links of this run

Failed run? Start the same query again: a new run re-collects, nothing is duplicated.
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

Passing looks like `OK` (218 tests), `pass 60`, a finished build and no lint output.

## How to test manually

You need `YOUTUBE_API_KEY` in `src/api/.env`.

1. `cd src && ./run-local.sh`, then open the UI at `http://localhost:5173/`.

2. Save a query with **Videos** 2, **Comments per video** 20 and **Replies per comment** 10. Click **Start run**.

3. In a second terminal: `cd src/api && venv/bin/python manage.py collect_runs`.

4. Click **Refresh** and open the run. After the `commentThreads.list` rows come `comments.list` rows, one per comment that has replies, and none for the others.

5. In `http://127.0.0.1:8000/admin/` → Youtube comments, filter or sort by level: replies show their parent comment and the same video.

## Common errors

- **No `comments.list` requests.** Either **Replies per comment** is empty (or was set after the run started), or none of the run's top-level comments has replies.

- **A `comments.list` row with `HTTP 404`, but the run completed.** That comment was deleted in the meantime. Its thread was skipped.

- **The run failed with `HTTP 403: quotaExceeded`.** The quota ran out. The run still reports what it stored. Start the same query again after the quota resets (midnight Pacific time) to complete the data.

## Known gaps

- A run interrupted by a crash (not an API error) stays `running`, as noted on page 14. Re-running the query still completes the data.

- Comments and replies are not shown in the app yet. They are visible in the admin.
