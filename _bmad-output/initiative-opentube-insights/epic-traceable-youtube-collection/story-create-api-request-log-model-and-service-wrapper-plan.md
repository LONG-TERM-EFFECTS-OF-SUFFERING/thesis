---
title: 'Create API request log model and service wrapper'
type: 'feature'
ticket: '4'
created: '2026-10-05'
status: 'built'
baseline_revision: 'e7e5bf74ba222ac453c4e77d3a95c0748fab0c0e'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context:
  - '{project-root}/docs/database_schema.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing records the YouTube API calls a collection run makes, so a dataset cannot be audited request by request (US-013). Later collection stories (US-015 onward) need one place that makes those calls.

**Approach:** Add an `ApiRequestLog` model (`api_request_logs`) and one wrapper function, `call_youtube(run, endpoint_name, params, *, api_key, transport=None)`. For every call it records the endpoint, parameters, HTTP status, quota cost, start and finish timestamps, item count, page tokens and errors. It never stores response bodies, the API key or YouTube resource IDs.

## Boundaries & Constraints

**Always:** Columns, types, nullability and `on_delete` match `api_request_logs` in `docs/database_schema.md`, including the unique (`collection_run`, `request_sequence`) and the `finished_at >= started_at` check, validated on Compose PostgreSQL.
- `endpoint_name` is the YouTube `resource.method` name (`search.list`, `videos.list`, `channels.list`, `commentThreads.list`, `comments.list`). It covers the backlog's "endpoint, method", since every call is an HTTP GET.
- Quota cost comes from a fixed per-endpoint table (`search.list` 100, the others 1). An endpoint not in the table is rejected before any request or log.
- The log row is created before the request, with `started_at`, and completed afterwards. A crash mid-call therefore leaves a row with `finished_at` null.
- `request_sequence` is 1-based per run.
- `YOUTUBE_API_KEY` is read through `env_str` with no default. The key goes into the request URL only, never into `request_params`, `error_message` or logger output.
- `params` containing `key` is rejected.
- No test reaches `googleapis.com`: tests inject `transport`, and one transport test stubs `urlopen`.

**Decisions:** The resource-ID parameters `id`, `channelId`, `videoId` and `parentId` are stored in `request_params` as `{"redacted_count": <number of comma-separated values>}`. `error_message` is `"HTTP <status>: <comma-joined error.errors[].reason codes>"` for an HTTP error (just `"HTTP <status>"` when the body has no reasons), and the exception class name for a network or decode failure. It never holds YouTube's free-text `error.message`.

**Never:** No YouTube discovery logic or callers (US-015). No run totals or count/quota columns on `CollectionRun` (US-012). No request-log endpoint or UI (US-014). No retries or backoff. No `google-api-python-client` or other new dependency: stdlib `urllib`, as in `query_translation._post_json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Success | `search.list`, 200 with 5 `items` and `nextPageToken` | payload returned; log: sequence 1, status 200, quota 100, items 5, next token stored, `finished_at` set, no error | No error expected |
| Sequence | second call on the same run | `request_sequence` 2 | No error expected |
| Page token | params include `pageToken` | stored in `page_token_sent`; `part`/`fields` copied to their columns | No error expected |
| Resource IDs | `videos.list` with `id=a,b,c` | log's `request_params` has `"id": {"redacted_count": 3}`, and no ID value anywhere in the row | No error expected |
| HTTP error | 403 with YouTube error body (`quotaExceeded`) | log: status 403, quota cost kept, `finished_at` set, `error_message` `"HTTP 403: quotaExceeded"`, items 0 | `YouTubeApiError` raised |
| Network error | `URLError` / timeout | log: status null, `finished_at` and `error_message` set | `YouTubeApiError` raised |
| Bad JSON | 200 with a non-JSON body | log: status 200, error set | `YouTubeApiError` raised |
| Unknown endpoint / `key` in params | `playlists.list`, or `params={"key": ...}` | no request, no log | `ValueError` |
| Key secrecy | any call | API key absent from the log row and logger output | No error expected |
| DB rules | duplicate (run, sequence); `finished_at < started_at` | not saved | `IntegrityError` |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` -- add `ApiRequestLog` after `CollectionRun`, using its idioms (UUID pk, `db_table`, `CheckConstraint(condition=…)`, docstring `__str__`). `related_name="request_logs"`. Generate `0006` with `makemigrations core`.
- `src/api/core/youtube_client.py` (new) -- `call_youtube`, `YouTubeApiError(RuntimeError)`, `QUOTA_COSTS`, `_get_json(url)` transport. Copy `query_translation._post_json`: stdlib `urllib`, `TIMEOUT_SECONDS`, one `ponytail:` comment, and the except tuple `(OSError, ValueError, http.client.HTTPException)`. Base URL `https://www.googleapis.com/youtube/v3/<resource>`. Import-safe: no env reads at import.
- `src/api/opentube_insights_api/settings.py` -- `YOUTUBE_API_KEY = env_str("YOUTUBE_API_KEY")` beside `LLM_API_KEY`, with the same no-default comment. `src/api/.env.example` and `src/docker-compose.yml` already declare it.
- `src/api/core/admin.py` -- register `ApiRequestLog`, every field read-only, filtered by `endpoint_name`; logs are evidence.
- `src/api/core/tests.py` -- `ApiRequestLogModelTests` (DB rules) and `CallYouTubeTests` (injected transport), plus `GetJsonTransportTests` that stubs `urllib.request.urlopen` like `PostJsonTransportTests`.
- Do not touch views, serializers, urls or `src/ui`.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/models.py` + migration `0006` -- `ApiRequestLog` -- the audit record.
- [x] `src/api/opentube_insights_api/settings.py` -- `YOUTUBE_API_KEY` -- the secret, read through the env helper.
- [x] `src/api/core/youtube_client.py` -- wrapper and transport -- the single path for YouTube calls.
- [x] `src/api/core/admin.py` -- read-only registration -- local inspection.
- [x] `src/api/core/tests.py` -- one test per matrix row, plus the transport test (URL, GET, key in query string, timeout, HTTPError mapping) -- covers the matrix.

**Acceptance Criteria:**
- Given a test, when the code is changed so the key or a resource ID reaches `request_params` or `error_message`, then a test fails.
- Given the HTTP-error test, when the wrapper stops completing the log on failure, then that test fails.

## Implementation Notes

- Transport contract: `url -> (status, payload dict)`, raising `YouTubeApiError` for every failure; `call_youtube` catches only that, so any other exception leaves the row with `finished_at` null (the crash case).
- Additions within the plan's rules: an empty `api_key` raises `ValueError` before logging (fail loudly); a 200 whose JSON is not an object raises `YouTubeApiError("ResponseNotAnObject")`; `part`, `fields` and `pageToken` stay in `request_params` and are also copied to their columns; `ParamValue` is `str | int` (bool excluded: `urlencode` would send `True`).
- Admin is view-only through `has_add_permission`/`has_change_permission`.
- Matrix audit: every row covered by `ApiRequestLogModelTests` (2), `CallYouTubeTests` (11) or `GetJsonTransportTests` (4); all ran OK on PostgreSQL, full suite 122 OK. Mutation-checked: key in params or logger, redaction off, no log completion on failure, free-text error message each fail a test. Thesis baseline: `d12d55662a88151103cdf2175383652f246d463e`.
- Review patches (pass 1) applied; full suite 123 OK on PostgreSQL. Side effect accepted: blocking log deletion in admin also blocks admin deletion of a run that has logs (Django checks cascade permissions); ORM cascades and the US-040 purge are unaffected, and runs are meant to be kept.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 2, low 4, false 1, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `REDACTED_PARAMS` misses `allThreadsRelatedToChannelId` (commentThreads.list); channel IDs logged verbatim past the purge | medium | patch | Confirmed: allowed endpoint, param absent from the set. Intent ("never stores YouTube resource IDs") has one reading for a channel ID; the Decisions list names the storage format, extending the set does not contradict it. Also added `relatedToVideoId` (search.list). |
| Same finding, `forHandle` / `forUsername` (channels.list) | false | reject | A handle or legacy username is researcher-typed lookup text, like `q`, not a resource `id`. Human may overrule. |
| Admin can delete request logs (single and bulk) | low | patch | Confirmed: no `has_delete_permission` override. Direct addition of one method. |
| `bool` param passes runtime and is sent as `True` | medium | patch | Confirmed: `ParamValue` is a hint only; AGENTS.md pitfall says reject `bool` explicitly. One `ValueError` guard before logging. |
| `redacted_count` counts `""` as 1 and `"a,"` as 2 | low | patch | Confirmed in `_loggable_params`; direct correction to count non-empty parts. |
| Over-long `pageToken`/`nextPageToken` raise `DataError` on the 255-char columns | low | reject | Real YouTube page tokens are short; unlikely in use and the fix adds length guards. |
| `test_json_that_is_not_an_object_is_an_error` does not assert the message | low | patch | Confirmed: only `http_status` asserted; add the `"ResponseNotAnObject"` assertion. |

## Design Notes

`call_youtube` writes the row in two steps (create, then `save(update_fields=…)`), not inside one transaction. A failed call still leaves its row even though the wrapper re-raises.

The sequence is `max(request_sequence) + 1` for the run. The unique constraint is the backstop if two writers race.

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test core` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.

**Manual checks:**
- In `manage.py shell`, call `call_youtube` with a fake `transport` on an existing run, then open `/admin/`: the log row shows every field, read-only, and no API key.
