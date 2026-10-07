---
title: 'Add YouTube collection service tests'
type: 'chore'
ticket: '4'
created: '2026-10-05'
status: 'done'
baseline_revision: '761374c5be89a146dc3a29b7daefcf7a9c6bfb02'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** US-034 asks for collection tests covering behavior, request logging, dedupe and error handling, all with controlled responses. Most already exist from US-013 and US-015. Three gaps remain:
- No test checks the request-log rows a collection writes.
- No test runs the real HTTP path, `urlopen` → `_get_json` → `call_youtube` → `collect_run`. Every collector test injects `transport`, and the runner test patches `_get_json`; this is the AGENTS.md "transport faked in every test" pitfall.
- No test uses a realistic YouTube payload.

**Approach:** Add tests only. Two documented-shape fixture constants (a full `search.list` response and a `quotaExceeded` 403 error body), a request-log test for a multi-page collection, and end-to-end tests that run `manage.py collect_runs` with only `urllib.request.urlopen` stubbed.

## Boundaries & Constraints

**Always:**
- Tests live in `src/api/core/tests.py`, beside `CollectRunTests`, reusing its helpers and `_FakeHttpResponse`.
- The fixtures follow the YouTube Data API v3 documented response shape: `kind`, `etag`, `nextPageToken`, `regionCode`, `pageInfo`, and `items[]` with `id.kind`/`id.videoId` and a `snippet` holding `publishedAt`, `channelId`, `title`, `description`, `thumbnails`, `channelTitle`, `liveBroadcastContent` and `publishTime`.
  - At least one title is HTML-escaped and one item is not a video (`id.kind` `youtube#channel`, with no `videoId`).
  - IDs are invented, 11 characters. A comment says the payload is shaped after the documentation, not captured.
- The error fixture is `{"error": {"code": 403, "message": ..., "errors": [{"reason": "quotaExceeded", "domain": "youtube.quota", "message": ...}]}}`.
- The end-to-end tests patch only `urllib.request.urlopen`, so `_get_json`, `call_youtube`, `collect_run` and the command all run for real.
- No test reaches `googleapis.com`.
- Each new test must fail when the behavior it covers is removed. Check that once by mutation and record it in Implementation Notes.
- Validated on Compose PostgreSQL.

**Never:** No product code changes. If a new test exposes a defect, stop and report it instead of fixing it. No moving or splitting existing tests. No new dependencies or test frameworks. No live API key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Request log per page | cap 60; page 1 = 50 items + `nextPageToken` `P2`; page 2 = 10 items | 2 `ApiRequestLog` rows, sequence 1 and 2, `endpoint_name` `search.list`. Row 1: `page_token_sent` null, `next_page_token_received` `P2`, `items_returned` 50. Row 2: `page_token_sent` `P2`, `items_returned` 10, `request_params.maxResults` 10. Both: status 200, `quota_cost` 100, `finished_at` set, no error, key absent | No error expected |
| Real path, success | `collect_runs` with `urlopen` serving the two-page search fixture (5 items + `nextPageToken`, then 2 items), cap 5 | run `completed`; two log rows (second with `pageToken` and `maxResults` 2); videos = the fixture's distinct video items (channel item skipped); the escaped title stored unescaped; each request URL is `https://www.googleapis.com/youtube/v3/search?...` with `key`, a GET, timeout 30 | No error expected |
| Real path, quota error | `collect_runs` with `urlopen` raising `HTTPError(403)` with the error fixture body | run `failed`, `error_message` `HTTP 403: quotaExceeded`; log row status 403, `error_message` the same, `finished_at` set; run totals 1 request / 100 units; the fixture's free-text `message` stored nowhere | none raised by the command |
| Dedupe on the real path | the search fixture contains the same `videoId` twice | linked once; `total_videos_discovered` counts it once | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/tests.py` `CollectRunTests` (around line 2309) -- helpers `make_run`, `transport(pages)`, `collect` and `linked_ids`, plus module helpers `_search_items` and `_ids`. Add the request-log test here.
- `src/api/core/tests.py` `_FakeHttpResponse` (around line 1406) -- the urlopen stand-in, which already takes `status`. `GetJsonTransportTests` (around line 2207) shows how to build an `HTTPError` with a body (`io.BytesIO`).
- `src/api/core/tests.py` `OPENAI_DRAFT_RESPONSE` (around line 1043) -- the precedent for a module-level fixture constant with a provenance comment. Put `YOUTUBE_SEARCH_RESPONSE` and `YOUTUBE_QUOTA_ERROR_RESPONSE` near `CollectRunTests`.
- New class `CollectRunsEndToEndTests(APITestCase)`: call `call_command("collect_runs", stdout=io.StringIO())` under `override_settings(YOUTUBE_API_KEY="secret-yt-key")` and `patch("urllib.request.urlopen", ...)`.
- Do not touch `core/collection.py`, `core/youtube_client.py`, models or migrations.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/tests.py` -- the two fixture constants -- realistic controlled responses.
- [x] `src/api/core/tests.py` -- the request-log test in `CollectRunTests` -- logging during collection.
- [x] `src/api/core/tests.py` -- `CollectRunsEndToEndTests` (success, quota error, dedupe) -- the real HTTP path.

**Acceptance Criteria:**
- Given the end-to-end success test, when `_get_json` stops passing `timeout=TIMEOUT_SECONDS` or builds a URL without the `/youtube/v3/search` path, then that test fails. This shows the real path runs.
- Given the quota-error test, when `_http_error_message` starts including YouTube's free-text `message`, then that test fails.
- `makemigrations --check --dry-run` reports no changes and no product file differs from the baseline.

## Implementation Notes

- Added `YOUTUBE_SEARCH_RESPONSE`, `YOUTUBE_SEARCH_LAST_PAGE`, `YOUTUBE_SEARCH_PAGE_1_RESULTS`, `YOUTUBE_SEARCH_VIDEO_IDS` and `YOUTUBE_QUOTA_ERROR_RESPONSE` just above `CollectRunTests`, with `_search_result` building each item.
  - Page 1 (`YOUTUBE_SEARCH_RESPONSE`) has exactly 5 items for `maxResults=5`: the escaped title, the `youtube#channel` result, the repeated `videoId`, and 3 distinct videos in all. It carries `nextPageToken` `CAUQAA`.
  - Page 2 holds the other 2 videos and no `nextPageToken`. With cap 5 the real path pages once more, sending `pageToken=CAUQAA` and `maxResults=2`.
- `serve_search` serves each page once, keyed by `pageToken`. An unknown or repeated token raises `AssertionError`, so a paging regression fails fast instead of hanging.
- The end-to-end helpers are typed: a `_SentRequest` NamedTuple with `url: str`, plus a `_UrlOpen` callable alias.
- `CollectRunTests.test_each_search_page_writes_one_request_log_row` covers the request-log row.
- `CollectRunsEndToEndTests` patches only `urllib.request.urlopen`. The quota test reuses `_youtube_http_error`. "Stored nowhere" is checked by dumping every `CollectionRun` and `ApiRequestLog` row.
- Mutation check (Compose PostgreSQL). Each mutation was applied to product code, the target test was run, and the file was restored. Every one failed the target test:
  - `pageToken` never sent → success test (fails fast on the repeated request)
  - last page `maxResults` not shrunk → success test
  - no `timeout=TIMEOUT_SECONDS` → success test
  - URL without the resource path → success test
  - YouTube free-text `message` appended in `_http_error_message` → quota test
  - `in seen` dedupe removed → dedupe test (IntegrityError → run failed)
  - `html.unescape` removed → success test
  - channel item not skipped → success test
  - `page_token_sent`, `next_page_token_received`, `items_returned` or success `finished_at` not logged → request-log test
  - `key` added to `request_params` → request-log test
  - error `response_http_status` not logged → quota test
- Pre-existing ruff E731 at `SavedQueryDraftApiTests` (a lambda) is untouched; it is not part of this change.
- Verified by orchestrator: full suite 146 OK on PostgreSQL; `git diff --stat` on `core/` excluding `tests.py` is empty. Thesis baseline: `144c6afd02e432c1c2ce3d13f4cc7d522d01ede4`.
- Frozen row 'Real path, success' amended by the human (2026-10-05) to the realistic two-page fixture from the review fix. Review patches applied; full suite 146 OK on PostgreSQL; product diff empty.
- Deferred repeated-`nextPageToken` loop fixed at the user's request in `src/api` commit `922bf33` on this branch: `_discover_videos` stops when the new token equals the one just sent; `test_repeated_page_token_stops_paging` fails (not hangs) without it. Full suite 147 OK on PostgreSQL.

## Plan Change Log

- 2026-10-05, review fix: the search fixture became two pages so that every page honours `maxResults`. As a result, the "Real path, success" row now produces two log rows, not one. The second request is asserted to carry `pageToken` `CAUQAA` and `maxResults` 2. The frozen matrix itself is left unchanged.

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 2, false 0, maybe-false 0, defer 1.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `serve_search` serves the same page and token forever; a regression leaving fewer than `cap` distinct videos hangs the suite | medium | patch | Confirmed: stub ignores `pageToken`; `_discover_videos` loops while the token is present. Fix: serve pages by token, raise on an unknown token. |
| `YOUTUBE_SEARCH_RESPONSE` returns 7 items for `maxResults=5` | low | patch | Confirmed against `pageInfo.resultsPerPage` 5. Direct correction: a realistic two-page fixture, which also exercises `pageToken` on the real path. |
| New end-to-end helpers have untyped parameters (implicit `Any`) | low | patch | Confirmed; AGENTS.md "avoid `Any`". Direct correction: annotate. |
| Implementer report: `collect_run` re-requests a repeated `nextPageToken` forever when every result is a duplicate | medium | defer | Confirmed in `core/collection.py` `_discover_videos`: no check that the token changed. Product code (US-015), out of this tests-only story. Logged in deferred-work. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test` -- expected: OK.
- `cd src/api && git diff --stat 761374c -- core/ ':!core/tests.py'` -- expected: empty.
