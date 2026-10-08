# 24 - Store comment raw payloads, quota and errors

Story: US-023, Store comment raw payloads, quota and errors.

Status note: this document describes the US-023 implementation **after** the code review of 2026-10-07 and the fixes that followed it. Like US-034 (page 15) and US-020 (page 21), this story added **tests only**.

## What this story added

US-023 asks that comment and reply collection be auditable: payloads stored, quota use stored, errors stored, and everything covered by the 30-day purge. By the time it was built, US-021 (page 22) and US-022 (page 23) already did the storing:

| US-023 asks for | already provided by |
| :-- | :-- |
| comment and reply raw payloads | `raw_payload` on every `youtube_comments` row |
| quota use | one request-log row per `commentThreads.list` / `comments.list` call, plus the run totals |
| errors | the error on the request-log row; on the run when it is fatal |
| purge coverage | **US-040** (agreed with the researcher), which deletes comments and replies by `last_fetched_at` |

What was missing was **proof that it all holds together**. This story adds two end-to-end tests that collect a realistic run through the real HTTP code, with only Python's network call faked, and then audit everything the run left behind.

## Why this matters

The thesis's claim is that a dataset can be audited: what was requested, what it cost, what failed, and what came back. Request logs are kept even after the 30-day purge deletes YouTube data, so they must **never** contain YouTube data themselves. One test now checks every log row of a full run for leaked IDs, comment text or the API key.

## Key concept: the audit run

The first test builds a run designed to hit every branch at once:

```text
saved query: 2 videos, 5 comments per video, 5 replies per comment

video A  -> comments disabled          (403 commentsDisabled -> skipped)
video B  -> thread 1 with 2 replies
         -> thread 2 whose parent was deleted (404 -> skipped)
```

After collecting it, the test checks:

| check | what it proves |
| :-- | :-- |
| each comment's and reply's `raw_payload` equals the exact item served | payloads are stored whole, unchanged |
| 7 log rows, in order, with the right endpoint and quota cost | every call is logged |
| run totals = (7 requests, 106 units) = the sum of the log rows | the run's totals and its logs agree |
| the `commentsDisabled` and `404` rows keep status, reason and finish time; the run is still `completed` | skipped errors are recorded, not hidden |
| comment rows store `videoId`, and reply rows `parentId`, as `{"redacted_count": 1}` | IDs are redacted in the log |
| the JSON of **all** log rows contains no video, comment or reply ID, no comment text and not the API key | logs hold no YouTube data |

The second test changes one thing: the reply request returns `403 quotaExceeded`. The run must end `failed` with that message, keep the comments already stored, and still have totals equal to its log rows (6, 105).

## Key concept: proving the tests can fail

A test that cannot fail proves nothing (the AGENTS.md pitfall). So each assertion was checked by **breaking the code on purpose** and confirming the test fails, then restoring it. The breakages included:

- removing `videoId` or `parentId` from the redaction list;
- skipping the run-totals update for one endpoint;
- giving `comments.list` the wrong quota cost;
- dropping the error message or finish time on a failed request;
- putting the API key into the logged parameters;
- storing only part of a comment as its payload.

One check could not be tested that way: that no **comment text** leaks into a log. No code writes text into a log, so there was nothing to remove. The review caught that gap. It was closed by writing a comment's text into a log row inside the test and confirming the test then fails.

## File-by-file explanation

### `src/api/core/tests.py`

- `_AUDIT_THREADS` and `_AUDIT_REPLIES`: the served comment threads and replies, kept as module values so the test can compare stored payloads with them exactly. One thread carries an author's `textOriginal`, so there is real text to look for.

- `CollectRunsEndToEndTests.start_audit_run(reply_error=None)`: sets up the audit run, optionally making the reply request fail.

- `assert_totals_match_logs`: checks that the run's request and quota totals equal its log rows.

- `test_audit_run_stores_payloads_quota_and_errors` and `test_quota_error_on_replies_fails_the_run_and_keeps_totals`: the two tests above.

No product file changed.

## How the pieces connect

```text
collect_runs (real code)
   '-- every YouTube call -> call_youtube
          |-- ApiRequestLog row: endpoint, redacted params, quota, status, error, times
          |-- run totals += 1 request, + quota cost
          '-- urlopen  <- the only fake

then the test reads back:
   YouTubeComment.raw_payload      == what was served
   ApiRequestLog rows              == every call, nothing secret
   CollectionRun totals            == sum over the log rows
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py test core.tests.CollectRunsEndToEndTests
```

Passing looks like `OK` (220 tests). The second command runs only the end-to-end class.

## How to test manually

This story adds no screen. To see the redaction for yourself after a real collection with comments (see page 23), open `http://127.0.0.1:8000/admin/` → Api request logs → a `commentThreads.list` row. Its request params show `"videoId": {"redacted_count": 1}`, never the video ID itself.

## Common errors

- **A script stops at `cp: overwrite '...'?`** In this environment `cp` is aliased to `cp -i`, which asks before overwriting. In scripts, use `command cp -f` (or `\cp`).

## Known gaps

- Purge coverage for comments and replies is proven by US-040's tests (page 26).
