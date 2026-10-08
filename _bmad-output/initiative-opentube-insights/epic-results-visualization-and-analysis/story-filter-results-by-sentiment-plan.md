---
title: 'Filter results by sentiment'
type: 'feature'
ticket: '4'
created: '2026-10-08'
status: 'done'
baseline_revision: '63fdb119e9a2d767632c82c5ece1bd4094882749'
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

**Problem:** A researcher cannot narrow results to one audience reaction group, for example only negative comments, so groups cannot be compared (US-030).

**Approach:** Add a `sentiment` label filter, one of `positive`, `negative`, `neutral`, `mixed` or `unknown`, to the run detail's Sentiment table (see Decisions). It reuses the existing sentiment rows of each collection run's **latest** sentiment pass (US-026's rule), so a label always comes from a known model and version.

## Boundaries & Constraints

**Always:**
- **The parameter** is `sentiment=<label>`. Any other value is 400 with a message on `sentiment`, and an empty value means "not set" (US-029's convention).
- **Model context:** the latest-pass rule and the model filter of US-026 apply. A label is matched only on rows whose `model_name`/`model_version` equal that pass's report, so a filtered view never mixes models.
- **Scope:** existing project and run scoping stays as it is, and another owner's data never appears.
- **UI:** a native `<select>` of the five labels plus "All". The active sentiment filter is stated in words, labels are text, not colour alone, and the late-response rule and the reset on project/run change apply.
- **Purity:** parameter parsing is pure and tested. No `any`. JSDoc on new exports.
- Validated on Compose PostgreSQL.

**Decisions** (approved by the human on 2026-10-08):
- **Placement:** the filter applies to the run detail's Sentiment table only, through `GET /api/projects/<p>/runs/<r>/sentiment/?sentiment=<label>&page=N`. The Results card is not filtered by sentiment.
- **Counts:** while a label is selected, the summary's label counts keep describing the whole pass. The response's `count`, `next` and `previous` describe the filtered rows, and the echo `"sentiment_filter": "<label>" | null` is added to the response.

**Never:**
- No charts (US-028).
- No re-running sentiment.
- No multi-label selection.
- No saved filter presets.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Filtered rows | `sentiment=negative` on a pass with 2 negative and 3 other rows | only the 2 negative rows; `count` 2; `sentiment_filter` `negative`; the summary's label counts unchanged (the whole pass) | No error expected |
| Paging with a filter | 60 negative rows among 100 | page 1 has 50 negative rows and `next` keeps `sentiment=negative`; page 2 has 10 | No error expected |
| No match | `sentiment=mixed` with none | `results` empty, `count` 0, summary still shown | No error expected |
| Bad value | `sentiment=angry` | no data | 400 on `sentiment` |
| Empty value | `sentiment=` | same as no filter; `sentiment_filter` null | No error expected |
| Other model rows | a stray row of another model version labelled negative | not included | No error expected |
| No pass | run with no sentiment pass, `sentiment=positive` | `sentiment: null`, no rows | No error expected |
| UI | user picks "Negative" | the table shows only negative rows, page 1, and says "Showing negative comments" | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/views.py` -- `CollectionRunSentimentView.get_queryset` (US-026) adds `sentiment_label=<label>` when the parameter is set. A pure `parse_sentiment_filter(query)` sits beside `parse_results_filters` (US-029). The Results card is untouched (Decisions).
- `src/api/core/tests.py` -- extend `SentimentResultsApiTests` (one test per row) and add parser tests.
- `src/ui/src/apiClient.ts` -- `getRunSentiment(projectId, runId, page, sentiment?, signal)`.
- `src/ui/src/App.tsx` -- a `<select>` above the Sentiment table. A change resets to page 1, and the selection resets when another run is selected.
- `src/ui/src/sentimentFormat.ts` or a small new helper -- the "Showing … comments" sentence, tested.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/views.py` -- the parser, the filter and the `sentiment_filter` echo.
- [x] `src/api/core/tests.py` -- API and parser tests.
- [x] `src/ui/src/apiClient.ts` + helper + tests.
- [x] `src/ui/src/App.tsx` -- the selector.

**Acceptance Criteria:**
- Given the other-model test, when the filter matches labels without the model filter, then the stray row appears and the test fails.
- Given the filtered-rows test, when the summary's label counts are computed from the filtered rows, then they change and the test fails.

## Implementation Notes

- The label is validated in `get_queryset` after the run is resolved, so a foreign or missing run is still 404 and a bad value on a run without a pass is still 400.
- The `<select>` shows only for a run whose pass is known and whose data is not purged. It sits in its own JSX slot, and the loading state carries `passKnown`, so it stays mounted (and focused) while another page of that pass loads. Its options use the lowercase label values, matching the counts and the table; "All" clears the filter. A purged run shows neither the select nor the "Showing … comments" sentence.
- `parse_sentiment_filter` reads every `sentiment` value of a `QueryDict`; more than one non-empty value is a 400 on `sentiment`.
- Re-selecting the same run (Refresh) keeps its label filter; selecting another run, or switching project, starts unfiltered.
- An empty filtered page reads "No <label> comments" instead of "No comments classified".

- Orchestrator check: backend 324 OK on PostgreSQL, migrations clean; UI 84 pass, build and lint clean. UI baseline `0180e11c60c20e49051671c50113fe40f7809562`; thesis baseline `975f76dd7d8c7dbb8688042d8f751a89edfa79b8`.

- Review patches (pass 1) applied: repeated `sentiment` rejected (`QueryDict.getlist`); select rendered only for a known pass; select and filter sentence hidden on purged runs (model and counts still shown).

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 3, false 0, maybe-false 0, defer 1.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| A repeated `sentiment` parameter is silently accepted (`QueryDict.get` returns the last value), including the multi-label form ruled out | low | patch | Confirmed. Reject more than one value with 400 on `sentiment`; parser tests with a real `QueryDict`. |
| Same last-value behavior in US-029's `parse_results_filters` | low | defer | Pre-existing (US-029), not caused by this change; logged in deferred-work. |
| The label `<select>` flashes while the first request loads and stays in the error state on runs without a pass | low | patch | Confirmed in the render condition. Render only when a pass is known. |
| On a purged run the select and "Showing … comments" render above "Data purged on" with no table | low | patch | Confirmed. Hide both when `data_purged_at` is set. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass.

**Manual checks:**
- With the US-026 seeding snippet (page 31), open the run, pick each label, and check that the table shows only that label while the counts stay.
