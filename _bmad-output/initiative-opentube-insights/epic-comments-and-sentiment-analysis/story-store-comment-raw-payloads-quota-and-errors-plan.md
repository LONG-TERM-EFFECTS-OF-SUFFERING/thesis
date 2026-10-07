---
title: 'Store comment raw payloads, quota and errors'
type: 'chore'
ticket: '3'
created: '2026-10-07'
status: 'done'
baseline_revision: '43659ea46aa2d21eb49b9d53b1e62ef7bd51a30c'
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

**Problem:** US-023 asks that comment and reply payloads, quota use and errors be stored, and that comments and replies be covered by the 30-day purge. US-021 and US-022 already store all of these, and their unit tests check each piece with an injected transport. Three proofs are still missing:
- run totals that include comment and reply requests;
- ID redaction in comment and reply request logs (the log rows outlive the purge, so they must hold no YouTube IDs or comment text);
- one full run on the real HTTP path that checks payloads, quota and errors together.

**Approach:** Add tests only: one end-to-end audit test plus small focused assertions. Purge coverage moves to US-040 (approved by the human on 2026-10-07), which will delete comments and replies by `last_fetched_at`.

## Boundaries & Constraints

**Always:**
- Tests live in `src/api/core/tests.py`. Reuse `CollectRunsEndToEndTests` (only `urllib.request.urlopen` stubbed, a fake that raises on any unexpected request) and the existing fixtures and helpers: `_comment_thread`, `_reply_item`, the `commentsDisabled` and 404 bodies.
- **The audit run:**
  - 2 videos. Video A has comments disabled. Video B has 2 top-level comments, one with 2 replies and one whose parent returns 404.
  - Limits: 5 comments per video and 5 replies per comment.
- **Assertions after the audit run:**
  - every stored comment and reply has `raw_payload` equal to the exact item served;
  - one log row per request in order, `endpoint_name` and `quota_cost` per endpoint;
  - `run.total_api_requests` = number of log rows and `run.total_quota_units` = sum of their `quota_cost`;
  - the `commentsDisabled` and 404 rows keep `response_http_status`, an `error_message` of status plus reason, and `finished_at`, while the run is `completed` with `error_message` null;
  - every `commentThreads.list` row has `request_params["videoId"] == {"redacted_count": 1}`, and every `comments.list` row has `request_params["parentId"] == {"redacted_count": 1}`;
  - serializing every `ApiRequestLog` row to JSON contains none of the served video IDs, comment IDs, reply IDs or comment texts, and not the API key.
- **A fatal error run:** a 403 `quotaExceeded` on the reply step leaves the run `failed` with that `error_message`. The failing log row records the error, and the run totals still equal the log rows.
- Each new assertion is mutation-checked once and recorded in Implementation Notes.
- No test reaches `googleapis.com`. Validated on Compose PostgreSQL.

**Never:**
- No product code changes. If a test exposes a defect, stop and report it.
- No purge (US-040).
- No new models, migrations or dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Audit run | the run described in Always | `completed`; payloads exact; log rows and run totals agree; error rows recorded; no IDs, text or key in any log row | No error expected |
| Fatal reply error | the audit run, but the reply request returns 403 `quotaExceeded` | `failed`, `error_message` `HTTP 403: quotaExceeded`; stored comments kept; totals equal the log rows | existing handlers |

</frozen-after-approval>

## Code Map

- `src/api/core/tests.py` `CollectRunsEndToEndTests` -- its `serve` routes by path and token, with instance attributes for responses (added in US-020). Extend it to serve `/commentThreads` and `/comments` from instance attributes too if needed, without changing existing tests' behavior.
- The `CollectRunTests` helpers `_comment_thread`, `_reply_item` and `_reply_page`, and the end-to-end `commentsDisabled` / 404 bodies from US-021 and US-022, are the fixtures. Build the served items as module values so the test can compare `raw_payload` to them exactly.
- `src/api/core/youtube_client.py` `REDACTED_PARAMS` is the source of the redaction rule. Do not edit it.
- Do not touch `core/collection.py`, `core/youtube_client.py`, models or migrations.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/tests.py` -- the audit run test.
- [x] `src/api/core/tests.py` -- the fatal reply error test.

**Acceptance Criteria:**
- Given the audit test, when `parentId` or `videoId` is removed from `REDACTED_PARAMS`, then the test fails.
- Given the audit test, when the run-totals update in `call_youtube` is skipped for one endpoint, then the totals assertion fails.
- `git diff --stat 43659ea -- core/ ':!core/tests.py'` is empty.

## Implementation Notes

- Added to `CollectRunsEndToEndTests`: `start_audit_run` (sets cap 2, comment and reply limits 5, and serves the fixtures through the existing `comments_response` / `replies_response` hooks; `serve` itself is unchanged), `assert_totals_match_logs`, `test_audit_run_stores_payloads_quota_and_errors` and `test_quota_error_on_replies_fails_the_run_and_keeps_totals`. Served items are module values `_AUDIT_THREADS` and `_AUDIT_REPLIES`, built with `_comment_thread` and `_reply_item`.
- With `max_videos_to_discover` 2, search page 1 yields `Qx7bT2mLp0A` (video A, comments disabled) and `Rk4nW8eYs1B` (video B). The audit run sends 7 requests for 106 units; the fatal run sends 6 for 105.
- The audit run asserts payloads, endpoint and quota per row, totals against the log rows, the two error rows, `finished_at` on every row, `videoId` / `parentId` redaction, and that the JSON of every log row holds no video, comment or reply ID, no comment text and not the API key.
- Mutation checks (each applied alone to product code, then reverted; both new tests run on Compose PostgreSQL):
  - `parentId` removed from `REDACTED_PARAMS`: audit fails (redaction and leaked thread IDs).
  - `videoId` removed from `REDACTED_PARAMS`: audit fails (redaction and leaked video IDs).
  - run-totals update skipped for `comments.list`: both tests fail on totals.
  - run-totals update skipped for `commentThreads.list`: both tests fail on totals.
  - `comments.list` quota cost changed to 2: both fail on the per-endpoint cost and hard totals.
  - `log.error_message` not set on failure: both fail.
  - `finished_at` not saved on failure: audit fails on rows 4 and 7, fatal test fails.
  - API key added to `request_params`: audit fails on the key.
  - comment `raw_payload` stores `topLevelComment` instead of the item: audit fails on payloads.
  - run `error_message` set to the class name: fatal test fails.
  - 403 treated like 404 in the reply step: fatal test fails.
- Not mutated alone: the comment-text check, since no product path writes text into a log row to remove; it is guarded by the assertion that the authored `textOriginal` is among the checked texts.
- No product code changed: `git diff --stat 43659ea -- core/ ':!core/tests.py'` is empty. Full suite on PostgreSQL: 220 tests OK; `makemigrations --check --dry-run`: no changes. `ruff check` reports one existing E731 in `SavedQueryDraftApiTests.post_draft`, not from this change.
- Orchestrator check: 220 OK on PostgreSQL; product diff empty; no stray files. Thesis baseline `af73b5abd4aec2684d25089821718eb00a104928`.
- Review patches (pass 1) applied by the orchestrator: text-leak assertion mutation-checked, guard comment reworded, `Mapping` parameter. Full suite 220 OK on PostgreSQL; product diff empty.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 3, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| The comment-text `assertNotIn` was never mutation-checked (plan: every new assertion is) | low | patch | Confirmed. Orchestrator ran a test-only mutation: writing "El MIO llegó tarde" into a log row's `error_message` before serialization makes the test fail with `secret='El MIO llegó tarde'`; reverted. |
| The fixture-guard comment claims it checks IDs | low | patch | Confirmed; reworded to what the line proves. |
| `start_audit_run(reply_error: tuple[int, dict[str, object]])` rejects the nested error fixture under a type checker (dict is invariant) | low | patch | Confirmed; parameter is now `Mapping[str, object]`. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && git diff --stat 43659ea -- core/ ':!core/tests.py'` -- expected: empty.
