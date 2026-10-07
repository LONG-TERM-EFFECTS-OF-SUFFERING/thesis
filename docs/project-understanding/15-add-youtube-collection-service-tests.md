# 15 - Add YouTube collection service tests

Story: US-034, Add YouTube collection service tests.

Status note: this document describes the US-034 implementation **after** the code review of 2026-10-05 and the fixes that followed it. It also covers a collector bug these tests surfaced, fixed on the same branch.

## What this story added

US-034 asks for tests that cover collection behavior, request logging, dedupe and error handling, all with controlled responses and no live API. Most of that already existed: US-013 and US-015 shipped their own tests. So this story first **audited** what was there and filled only three real gaps:

1. **Request logging during a collection.** Earlier tests checked the run's totals, but never the log rows a multi-page collection writes.

2. **The real HTTP path.** Every collector test replaced the network layer, so the path from `urlopen` through `_get_json` and `call_youtube` to `collect_run` never ran end to end.

3. **Realistic YouTube responses.** The tests built minimal fake items. Nothing looked like what YouTube actually sends.

It also adds one product fix: the collector could loop forever on a repeated page token.

## Why this matters

The thesis claims the collection is auditable and correct. Tests are the evidence for that claim, but only if they would fail when the behavior breaks. AGENTS.md records how this went wrong before: "a transport faked in every test so the real HTTP path never ran". A test that fakes the very code it should check passes for the wrong reason.

## Key concept: where to put the fake

Tests must never call YouTube, so something has to be faked. The question is **what**:

```text
collect_runs command
   -> collect_run
      -> call_youtube
         -> _get_json            <- earlier collector tests replaced this (transport=...)
            -> urllib.request.urlopen   <- the new end-to-end tests replace only this
```

The lower the fake, the more real code runs. The new end-to-end tests fake only `urlopen`, the standard-library function that would open the network connection. Everything above it runs for real: building the URL, the 30-second timeout, decoding the JSON, turning a 403 into `YouTubeApiError`, logging, paging, storing videos and the command.

## Key concept: realistic fixtures

A **fixture** is fixed input data a test uses. The new ones follow the response shape documented for the YouTube Data API v3, with `kind`, `etag`, `nextPageToken`, `pageInfo` and `items` holding `id` and `snippet`:

- `YOUTUBE_SEARCH_RESPONSE`: page 1, exactly 5 items for `maxResults=5`. It includes an HTML-escaped title, a **channel** result (no `videoId`, which must be skipped) and the same video twice (which must be linked once), plus a `nextPageToken`.

- `YOUTUBE_SEARCH_LAST_PAGE`: page 2, the remaining videos, with no `nextPageToken`.

- `YOUTUBE_QUOTA_ERROR_RESPONSE`: the body YouTube sends with a `403` when the daily quota is used up, with `reason: quotaExceeded`.

The IDs are invented, and a comment says the data is shaped after the documentation, not recorded from a live call.

The code review caught an earlier version that returned 7 items for `maxResults=5`, which YouTube never does. Splitting it into two pages fixed that and made the end-to-end test exercise paging as well.

## Key concept: a test must fail, not hang

The fake `urlopen` serves pages by `pageToken`, and **raises** if it is asked for a token it does not know or has already served. Without that, a bug that keeps paging would make the test loop forever, and a hanging test suite tells you nothing. With it, the bug shows up as a clear failure.

Each new test was also checked the AGENTS.md way: break the behavior on purpose (drop the timeout, remove dedupe, leak YouTube's error text and so on), confirm the test fails, then restore the code.

## The bug these tests found

While writing the stubbed tests, the implementer noticed a real collector bug. Suppose YouTube answers page 2 with the **same** `nextPageToken` it was just sent, and every result is a duplicate. The collector would then request page 2 again, and again, at 100 quota units each, until the quota ran out and YouTube answered `403`.

The fix in `_discover_videos` (`src/api/core/collection.py`) is one check: stop when the new token equals the one just sent. `test_repeated_page_token_stops_paging` covers it. Its fake raises on a third request, so without the fix the test fails quickly instead of hanging.

## File-by-file explanation

### `src/api/core/tests.py`

- Fixtures `YOUTUBE_SEARCH_RESPONSE`, `YOUTUBE_SEARCH_LAST_PAGE` and `YOUTUBE_QUOTA_ERROR_RESPONSE`, built with the helper `_search_result`.

- `CollectRunTests.test_each_search_page_writes_one_request_log_row`: a two-page collection writes two log rows. Each row has the right sequence, page token sent and received, item count, `maxResults` (shrunk on page 2), status, quota cost, finish time and no API key.

- `CollectRunTests.test_repeated_page_token_stops_paging`: the bug fix above.

- `CollectRunsEndToEndTests`, which runs `manage.py collect_runs` with only `urlopen` faked:
  - `test_search_pages_are_fetched_logged_and_stored`: two requests to `https://www.googleapis.com/youtube/v3/search`, a GET with timeout 30, the `key`, `pageToken` and a shrunk `maxResults` on page 2, two log rows, the channel item skipped and the title stored unescaped.
  - `test_quota_error_fails_the_run_with_reason_codes_only`: the run and its log row both read `HTTP 403: quotaExceeded`, the totals are 1 request and 100 units, and YouTube's free-text error message appears nowhere in the database.
  - `test_repeated_video_id_is_linked_and_counted_once`: dedupe on the real path.

- `_SentRequest` and `_UrlOpen`: small type definitions, so the fake's parameters are typed rather than `Any` (an AGENTS.md rule).

### `src/api/core/collection.py`

Only the repeated-token check described above.

## How the pieces connect

```text
CollectRunsEndToEndTests
   patch("urllib.request.urlopen", serve_search)   <- the only fake
   call_command("collect_runs")
      -> collect_run -> call_youtube -> _get_json -> urlopen (fake)
            page None  -> YOUTUBE_SEARCH_RESPONSE   (5 items, nextPageToken CAUQAA)
            page CAUQAA -> YOUTUBE_SEARCH_LAST_PAGE (2 items, no token)
            anything else -> AssertionError         (fail, never hang)
   assert: run, ApiRequestLog rows, YouTubeVideo rows, CollectionRunVideo links
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py test core.tests.CollectRunsEndToEndTests
```

Passing looks like `OK` (147 tests). The second command runs only the end-to-end class. If PostgreSQL refuses the connection, the database container is not running: `docker compose up -d db` starts it.

`--noinput` matters if an earlier test run was interrupted. Django then finds a leftover `test_opentube` database and would otherwise stop to ask whether to delete it.

## How to test manually

This story adds no screen and no endpoint. To see that the tests guard what they claim, break one thing on purpose and watch its test fail. For example, delete `timeout=TIMEOUT_SECONDS` in `_get_json` (`src/api/core/youtube_client.py`), run `CollectRunsEndToEndTests`, see `test_search_pages_are_fetched_logged_and_stored` fail, then restore the line with `git checkout core/youtube_client.py`.

## Common errors

- **`connection to server at "127.0.0.1", port 5432 failed: Connection refused`.** The Compose database is stopped. Run `cd src && docker compose up -d db`.

- **`Type 'yes' if you would like to try deleting the test database 'test_opentube'`.** A previous run was killed. Answer `yes`, or add `--noinput`.

- **`AssertionError: ... pageToken ...` inside a collector test.** The collector asked for a page the fake does not serve. That is the guard doing its job: something now pages differently than the test expects.

## Known gaps

- The fixtures follow YouTube's documented shape but were not captured from a live call. US-039 (validation with real YouTube topics) is where real responses get checked.
