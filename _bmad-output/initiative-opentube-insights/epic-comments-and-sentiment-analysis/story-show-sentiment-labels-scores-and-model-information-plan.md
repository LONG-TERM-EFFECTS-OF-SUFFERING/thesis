---
title: 'Show sentiment labels, scores and model information'
type: 'feature'
ticket: '5'
created: '2026-10-08'
status: 'done'
baseline_revision: 'c3f0ea32619428800d1d8729fc89a081c05edf68'
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

**Problem:** Sentiment results (US-025) are stored but visible only in the Django admin, without the model context needed to interpret them responsibly (US-026).

**Approach:**
- **API:** a read-only endpoint returns a collection run's sentiment results: the sentiment processing run's model name and version, status, dates and label counts, plus the per-comment rows (label, score, confidence and the comment's text).
- **UI:** the run detail in the Collection runs panel gains a **Sentiment** section showing the model name and version, the label counts and a table of comments with their label, score and confidence.

Until a real model is plugged in (US-025 part B), the section shows a clear "no sentiment yet" state. Everything is tested with stored fixture rows.

## Boundaries & Constraints

**Always:**
- **Scope:** the endpoint is scoped through `ProjectOwnerMixin.get_project()` and the run's project: another owner's run or another project's run is a 404, and writes are a 405.
- **Model context:** the response states `model_name` and `model_version` once, from the sentiment processing run's report, and every row's own `model_name`/`model_version` must match it. The UI shows the model name and version **above** the results, never only in a tooltip.
- **Numbers:** `sentiment_score` and `confidence` are returned as JSON numbers, or null. The UI shows the score with a sign and two decimals, and the confidence as a percentage. A null shows as `—`, never `0`.
- **Labels:** all five labels appear in the counts, including zeros. The UI marks labels with text, not colour alone (accessibility basics).
- **UI rules:** fetches follow the AGENTS.md late-response rule (an `AbortController` in a ref, an identity check, and the project and run ids). No `any`. JSDoc on new exports. Pure helpers for formatting, tested with `node --test`.
- Validated on Compose PostgreSQL.

**Decisions** (approved by the human on 2026-10-08):
- **Placement:** `GET /api/projects/<project_id>/runs/<run_id>/sentiment/`, named `project-run-sentiment`, shown as a `<h4>Sentiment</h4>` section in the run detail, after Discovery and before Requests.
- **Paging:** DRF `PageNumberPagination` on this view only, `page_size = 50`, `?page=N`. The response is `{"sentiment": {run summary} | null, "model_configured": bool, "count", "next", "previous", "results": [rows]}` (`model_configured` = whether `SENTIMENT_MODEL` is set, never its value; approved by the human on 2026-10-08). The run summary has `processing_run_id`, `status`, `error_message`, `model_name`, `model_version`, `started_at`, `finished_at` and `labels` (all five), and covers the whole run on every page. The summary's `labels` come from the pass's report (counts at classification time), so they survive the 30-day purge, and the rows shown are only those whose `model_name`/`model_version` equal the report's (amended by the human-approved review on 2026-10-08). Rows are ordered by comment level, then the comment's `youtube_published_at`, then id, so pages are stable. The UI has Previous and Next buttons.
- **Which run:** the most recent sentiment processing run of the collection run (a processing run whose `summary_payload` has a `model_name` key), by `created_at` then id. Older passes are reachable only in the admin.
- **Row shape:** `{comment_level, text_display, sentiment_label, sentiment_score, confidence, language_code, model_name, model_version}`. There are no YouTube IDs in the payload; the internal comment UUID is not needed by the UI.

**Never:**
- No running or re-running sentiment from the UI.
- No real model (US-025 part B).
- No charts (US-028) or filters (US-029, US-030).
- No editing of results.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Results | completed run with a completed sentiment run (stored fixture rows: positive, negative, neutral) | 200 with model name/version, status, label counts (all five keys) and the rows with label, score, confidence and text | No error expected |
| No sentiment | completed run without a sentiment processing run | 200 with `sentiment: null`; the UI shows "No sentiment results yet" and, while `SENTIMENT_MODEL` is unset, says no model is configured | No error expected |
| Failed sentiment | sentiment processing run `failed` | 200 with status `failed` and its error class name; the UI shows the failure, not an empty table | No error expected |
| Null numbers | a row with score or confidence null | JSON null; the UI shows `—` | No error expected |
| Foreign run | another owner's or another project's run | 404 | 404 |
| Write | POST | 405 | 405 |
| Purged | the collection run's comments were purged (`data_purged_at` set) | the summary keeps the report's label counts; the UI shows "Data purged on <date>" in place of the table | No error expected |
| Running pass | a sentiment pass still `pending`/`running` | shown with that status and its model name/version, no rows yet | No error expected |
| Paging | 120 sentiment rows | page 1 has 50 rows, `next` set; page 3 has 20; label counts equal on every page | No error expected |
| Latest pass | two sentiment runs for one collection run | the newer run's summary and rows only | No error expected |
| UI late response | the user switches run while a sentiment request is in flight | the stale response is dropped | abort + identity check |

</frozen-after-approval>

## Code Map

- `src/api/core/views.py`, `urls.py`, `serializers.py` -- `CollectionRunSentimentView(ProjectOwnerMixin, generics.ListAPIView)`, with the run looked up through `get_project()` (404 otherwise), `pagination_class` set on the view only, and `list()` overridden to add the `sentiment` summary beside the paginated rows. `select_related("comment")` avoids one query per row.
- `src/api/core/models.py` -- no change. `CommentSentiment` and `ProcessingRun` exist; the sentiment run is the one whose report has a `model_name` key, and The most recent one is shown (Decisions).
- `src/api/core/tests.py` -- a `SentimentResultsApiTests` class that builds `ProcessingRun` and `CommentSentiment` rows directly (no classifier needed).
- `src/ui/src/apiClient.ts` -- types, a guard and a fetcher, following `getCollectionRun`. Add `tests/sentimentApi.test.ts`.
- `src/ui/src/sentimentFormat.ts` (new) -- pure formatting helpers (score with a sign, confidence as a percentage, null as `—`), tested.
- `src/ui/src/App.tsx` -- a `<h4>Sentiment</h4>` section in the run detail (after Discovery, before Requests), loaded when a run is selected or refreshed, guarded like the run detail fetch. `App.css` for the table.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/serializers.py`, `views.py`, `urls.py` -- the sentiment endpoint.
- [x] `src/api/core/tests.py` -- one test per API matrix row.
- [x] `src/ui/src/apiClient.ts`, `sentimentFormat.ts` + tests -- types, guard, fetcher and formatting.
- [x] `src/ui/src/App.tsx`, `App.css` -- the Sentiment section.

**Acceptance Criteria:**
- Given the results test, when a row's model name or version differs from the run's, then the test fails (model context is consistent).
- Given the formatting tests, when a null confidence is formatted as `0%`, then the test fails.
- Given the running app with a sentiment run seeded in the Django shell, when the user opens the run, then the model name and version are visible above the results and each row shows label, score and confidence.

## Implementation Notes

- Label counts come from `summary_payload.labels` (a missing key defaults to 0), so they survive the purge; rows are filtered to the report's `model_name`/`model_version`. The UI shows "Data purged on <date>" in place of the table when the run's `data_purged_at` is set.
- `analyze_comments` (US-025 code) now builds the classifier before creating the pass and creates it with `summary_payload={"model_name", "model_version"}`, so a pending/running pass is visible to the endpoint; a classifier that fails to build keeps the old path (unnamed pass, failed with the exception's class name).
- Rows sort by `-comment__comment_level` (`top_level` sorts after `reply`, so descending puts top-level first), then `youtube_published_at` with `nulls_last=True` so PostgreSQL and SQLite page identically, then the sentiment row id.
- Scores and confidences use `DecimalField(coerce_to_string=False)` on the serializer only; the global `COERCE_DECIMAL_TO_STRING` is untouched.
- `isRunStatus` was extracted in `apiClient.ts` and reused by `isCollectionRun`.
- Mutation-checked: removing the `model_name` report filter, the newest-first order, the row filter by model version, report-based counts (rows-based counts fail the purge test), the pass being named at creation, the top-level-first order, the project scope, the number coercion or the pagination each fails at least one `SentimentResultsApiTests` test; a row with a different `model_version` fails the results test; a null confidence formatted as `0%` fails the format test.

## Plan Change Log

- 2026-10-08: the response gains a top-level `model_configured` boolean (`bool(settings.SENTIMENT_MODEL)`). The "No sentiment" matrix row needs the UI to say no model is configured while `SENTIMENT_MODEL` is unset, and the decided shape had no field the UI could read that from. Only the boolean is exposed, never the key's value.

- Orchestrator check: backend 296 OK on PostgreSQL, migrations clean; UI 73 pass, build and lint clean. UI baseline `adb75d88370a7f2c9fc38407008dd431ac3fcb14`; thesis baseline `c7ac26ec5ae11a5fd3cfd5b38ada8661eb1ea705`.

- Review patches (pass 1) applied: rows filtered by the report's model; label counts from the report; "Data purged on" in the UI; sentiment passes named at creation (`core/sentiment.py`). Backend 299 OK on PostgreSQL; UI 73 pass, build and lint clean.

## Review Triage Log

Pass 1 (quick lens): high 0, medium 2, low 2, false 0, maybe-false 0, defer 0; rejected 2.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Rows are not filtered by the report's model name/version, so a mixed pass would serve rows disagreeing with the stated model | low | patch | Confirmed: the unique key allows several versions per pass. Filter rows by the report's name and version. |
| After the purge the section shows zero counts although the report keeps them, and has no purge state | medium | patch | Confirmed: `CommentSentiment` cascades with the comment. Counts now come from the report; the UI shows "Data purged on" from the run's `data_purged_at`. Frozen row added with the human's approval. |
| A pending or running sentiment pass is invisible, because `model_name` is written to the report only at the end | medium | patch | Confirmed in `analyze_comments`. Write `model_name`/`model_version` into `summary_payload` when the pass is created; frozen row added. |
| `model_configured` added to a frozen response shape without approval | low | intent_gap → patch | The human approved keeping it; the frozen Decisions now include it. |
| Acceptance criterion 3 (manual browser check) has no evidence | — | reject | A manual check that needs seed data in the human's dev database; not a code defect. Listed as pending for the human. |
| UI late-response handling has no automated test | low | reject | No React render harness (deferred since US-007); same accepted gap as US-014 and US-027. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass.

**Manual checks:**
- Seed a sentiment run in `manage.py shell` (a `ProcessingRun` with a sentiment report and a few `CommentSentiment` rows for a collected run), open the run in the UI, and compare the section with `/admin/`.
