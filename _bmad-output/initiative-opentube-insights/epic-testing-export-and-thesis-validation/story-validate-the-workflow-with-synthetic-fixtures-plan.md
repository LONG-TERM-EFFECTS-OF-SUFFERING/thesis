---
title: 'Validate the workflow with synthetic fixtures'
type: 'chore'
ticket: '8'
created: '2026-10-09'
status: 'done'
baseline_revision: '96d37482a446ee4ff272db652e3d78a8d0c52f53'
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

**Problem:** Each stage of the workflow is tested on its own, but nothing runs the whole path in one go: natural-language draft, review and save, collection, processing, sentiment, and the results the screen shows. So the thesis cannot show that the complete workflow works without the live OpenAI and YouTube APIs (US-038).

**Approach:** Add one synthetic end-to-end validation (scope in Decisions). It drives the real API endpoints and the real `collect_runs` command over a small, fully synthetic fixture corpus. Only `urllib.request.urlopen` is stubbed, and the sentiment classifier is the existing test fake. Each stage's output is asserted with exact values.

## Boundaries & Constraints

**Always:**
- **One test, one path, in order, each step through its public entry point:**
  1. `POST .../queries/draft/` with a natural-language prompt. The draft comes from the stubbed LLM.
  2. `POST .../queries/` saves the reviewed parameters, edited from the draft.
  3. `POST .../queries/<q>/runs/` starts a run.
  4. `call_command("collect_runs")` collects. Normalization and sentiment then run automatically.
  5. `GET` the run detail, the run sentiment, the results summary (counts and the sentiment distribution the chart draws) and one CSV export.
- **The synthetic corpus:** one module-level fixture set, written for this test and clearly synthetic. It has no real channel, video or comment ids and no real people's text.
  - **Videos and channels:** 2 videos on 1 channel.
  - **Comments:** 3 top-level comments and 1 reply.
  - **Labels:** the texts are chosen so `FakeClassifier` labels them positive, negative and neutral.
  - **Cleaning:** at least one comment that a normalization rule changes.
  - **Form:** every response has the documented YouTube or OpenAI shape.
- **The stub** routes by URL host and path:
  - `api.openai.com` is served the draft;
  - the YouTube endpoints are served from the corpus;
  - anything else is an `AssertionError`.

  `LLM_API_KEY` and `YOUTUBE_API_KEY` are set to obvious test values with `override_settings`. No request leaves the process.
- **Exact assertions per stage:**
  - the draft's parameters;
  - the saved query's `query_source`;
  - the run's status, counters and request-log endpoints in order;
  - the processing report's counts and one `text_normalized`;
  - the sentiment pass's model and label counts;
  - the summary's counts and its `sentiment` entry;
  - the CSV's row count and `delete_by`.
- **Mutation check:** breaking any one stage fails the test, recorded in Implementation Notes. Examples: no normalization, sentiment off, the wrong `RETENTION_DAYS`.
- Validated on Compose PostgreSQL.

**Decisions** (approved by the human on 2026-10-09):
- **Scope:** an automated test only, run on every `manage.py test`. The thesis cites it and its output as the evidence. No demo loader and no synthetic model in `CLASSIFIERS`; a live demo uses real keys, or US-039.

**Never:**
- No real API calls, keys, ids or comments.
- No product code changes. A defect the test exposes is reported, not silently fixed.
- No new dependencies and no migrations.
- No UI render harness (that is US-037).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Full path | the corpus, both keys stubbed, `SENTIMENT_MODEL` set to the fake | run `completed`; 2 videos, 1 channel, 3 comments, 1 reply; normalization `completed` with its report; sentiment `completed` with positive/negative/neutral counts; summary `sentiment` entry equal to those counts; videos CSV with 2 rows | No error expected |
| Stray request | any URL outside the routed endpoints | the test fails at that request | `AssertionError` from the stub |
| Rerun | `collect_runs` again with no pending run | nothing new collected, no new requests | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/tests.py`:
  - `QueryTranslationEndToEndTests.post_draft` (around line 3412): how to POST the draft endpoint with only `urlopen` stubbed, and the OpenAI response shape it serves.
  - `CollectRunsEndToEndTests` (around line 6440): `collect`, `serve`, `_FakeHttpResponse`, `_SentRequest`, and the `YOUTUBE_*` and `_AUDIT_*` fixture shapes, including comment threads and replies. Reuse the helpers and the shapes; write new synthetic values.
  - `FakeClassifier` and `use_classifier` (around line 8122): the fake sentiment model and how it is configured.
  - `SavedQueryApiTests` / `CollectionRunStartApiTests`: the request bodies for saving a query and starting a run.
  - Add `SyntheticWorkflowTests(APITestCase)` near `CollectRunsEndToEndTests`.
- Read-only references:
  - `src/api/core/views.py`: the summary, run detail, sentiment and export endpoints;
  - `src/api/core/collection.py`: `collect_run` calls processing, then sentiment;
  - `src/api/core/purge.py`: `RETENTION_DAYS`.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/tests.py` -- the synthetic corpus constants, the URL router, and `SyntheticWorkflowTests` with the full-path, stray-request and rerun tests.

**Acceptance Criteria:**
- Given the full-path test, when `collect_run` stops calling processing, then the test fails at the processing stage.
- Given the full-path test, when `SENTIMENT_MODEL` is unset, then the test fails at the sentiment stage.
- Given any stage's endpoint returning a different count, then the test fails naming that stage (a `subTest` or a message per stage).

## Implementation Notes

- Baselines: API `96d37482a446ee4ff272db652e3d78a8d0c52f53` (frontmatter, branch `feature/US-038`), thesis `5c0fb3b3afb44f63560d68167226ab0dd87e8ce0`. Only `src/api` changes.
- Corpus and test live after `CollectRunsEndToEndTests`: `SYNTHETIC_*` constants built with the existing `_openai_response`, `_search_result`, `_video_item`, `_channel_item`, `_comment_thread` and `_reply_item` builders, new IDs (`UCsyntheticFixtureChan01`, `SynthVid001/002`, `UgxSynth*`). The full path sends 7 requests: 1 OpenAI, then search, videos, channels, 2 commentThreads, 1 comments (105 quota units). Each stage is a `subTest(stage=...)`: draft, save, start, collection, processing, sentiment, summary, export.
- The CSV check compares `delete_by - collected_at` to a literal 30 days, not `RETENTION_DAYS`, so a policy change fails it.
- Mutation check (product file changed, full-path test run, file restored); every one fails the named stage:
  - `collect_run` returns before `process_collection_run`: processing (error), sentiment, summary.
  - `analyze_comments` reads `SENTIMENT_MODEL` as empty: sentiment, summary.
  - `RETENTION_DAYS = 29`: export.
  - `_collect_replies` not called: collection, processing, sentiment, summary.
  - summary `replies` reports the top-level count: summary.
  - `urls_replaced` rule a no-op: processing.
  - draft drops `relevanceLanguage`: draft.
  - serializer always derives `query_source = manual`: save.
  - after review: `_search_params` drops `q`, `relevanceLanguage` and `publishedAfter`: collection (search.list `request_params` differ from the saved `structured_query_params`).
  - after review: commentThreads sent for an unknown `videoId`: collection, with the stray URL in the failure message (`self.unexpected`), then processing, sentiment, summary.
  - after review: with draft, save and start now stopping the test on failure (`stage=` message), the draft mutation gives one failure, not a cascade.
- No product defect found.

- Review patches (pass 1) applied, see the triage log. Re-verified: 351 OK on PostgreSQL, migrations clean, product diff empty, no non-synthetic values in the added lines.

- Orchestrator check: 351 OK on PostgreSQL with all three `SyntheticWorkflowTests` run; migrations clean; product diff empty.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 4, false 0, maybe-false 0, defer 0. One finding's sub-claim (HTML `textDisplay`) was false.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Collection's use of the reviewed query is never checked: the stub ignores the query string, and dropping `q`/`relevanceLanguage`/`publishedAfter` in `_search_params` still passed | medium | patch | Confirmed. The collection stage compares the search.list log's `request_params` with the saved `structured_query_params`; that mutation now fails. |
| A stray YouTube URL during collection never surfaces as the stub's error, because `collect_run` catches every exception and marks the run failed | low | patch | Confirmed. `serve` records unexpected URLs in `self.unexpected` and the collection stage asserts it is empty, naming the URL. |
| Builder defaults leak non-synthetic values (`@vecina`/`@vecino`, "Canal Movilidad", Cali tags, descriptions, `es` languages, `@canalmovilidad`) into the corpus and the CSV | low | patch | Confirmed. Synthetic wrappers override authors, channel, tags, languages, descriptions, titles, `localized` and the avatar URL. |
| Responses depart from the documented shape: `textDisplay` raw instead of HTML; no `etag`, and no `pageInfo` outside search | low | patch | Partly false: collection sends `textFormat=plainText`, so YouTube's `textDisplay` is plain text; the HTML rendering the implementer added was reverted. `etag` and `pageInfo` added to every list through `_synthetic_list`. |
| A failed draft/save/start inside a subTest cascades into `UnboundLocalError` in every later stage | low | patch | Confirmed. Those three steps run outside subTests with a `stage=` message; a broken draft now reports one failure. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py test core.tests.SyntheticWorkflowTests -v 2` -- expected: three tests, ok.
- `cd src/api && git diff --stat 96d37482a446ee4ff272db652e3d78a8d0c52f53 -- core/ ':!core/tests.py'` -- expected: empty.
