---
title: 'Show sentiment distribution chart'
type: 'feature'
ticket: '2'
created: '2026-10-09'
status: 'done'
baseline_revision: '8314d6dbf997226e0a415cff05a5d1ef6417e0a3'
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

**Problem:** Sentiment results exist only as five label counts and a table inside one run's detail. Nothing shows the distribution as a chart, so a researcher cannot see broad audience opinion patterns at a glance (US-028).

**Approach:** Draw a simple horizontal bar chart of the five sentiment labels in the results view (placement in Decisions), labeled with the collection dates of the data it counts. Plain HTML and CSS bars, with no chart library.

## Boundaries & Constraints

**Always:**
- **Never mix models.** Only rows of each collection run's **latest** sentiment pass count, and only rows whose `model_name`/`model_version` equal that pass's report (US-026's rule). If the counted rows come from more than one model name and version, there is one chart per model, headed with its name and version.
- **Count each comment once.** A comment that several runs found and classified counts once per model, with the label from the newest counted pass. This matches the card, where every comment counts once.
- **Every chart shows** the model name and version, the total counted, and for each of the five labels, in the fixed order `positive`, `negative`, `neutral`, `mixed`, `unknown`:
  - the label as text;
  - the count and the percentage (one decimal);
  - a bar whose length is proportional to the count.

  A zero-count label still shows its row. The meaning never depends on colour alone.
- **The collection date label.** Each chart states "Comments collected between X and Y", the min and max `CollectionRunComment.discovered_at` of the counted comments on this project's runs.
- **Owner and project scoping** as today: another owner's or project's rows never count.
- **The bars are accessible:** the chart is a list or table that a screen reader reads as label, count and percent; the bar itself is decorative (`aria-hidden`).
- **Purity:** the percentage and bar-width maths is a pure, tested TypeScript helper. No `any`. JSDoc on new exports. Python docstrings per the project template.
- Validated on Compose PostgreSQL.

**Decisions** (approved by the human on 2026-10-09):
- **Placement:** the chart sits in the Results panel's project card and is project-wide, built from every run of the project. It follows US-029's `date_from`, `date_to` and `video` filters: only comments on the matching videos count.
- **The API:** `GET /api/projects/<p>/results/summary/` gains `sentiment: [{model_name, model_version, total, labels: {<five labels>: n}, first_collected_at, last_collected_at}]`, ordered by model name then version. It is `[]` when nothing is counted. The chart reads from rows, so after the 30-day purge it empties, as the card's comment counts do.

**Never:**
- No chart or UI library and no new dependencies.
- No re-running sentiment and no change to stored rows or reports.
- No sentiment-label filter on the chart (US-030's filter stays in the run detail).
- No export (US-031, US-032).
- No migrations.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| One model | 2 positive, 1 negative, 1 neutral counted | one chart: total 4; positive 2 (50.0%), negative 1 (25.0%), neutral 1 (25.0%), mixed 0 (0.0%), unknown 0 (0.0%); dates shown | No error expected |
| Stale pass | an older pass of the same run labeled the comment differently | only the latest pass's label counts | No error expected |
| Stray row | a row of another model version inside the latest pass | not counted | No error expected |
| Shared comment | the same comment in two runs' latest passes, same model | counted once, with the newest pass's label | No error expected |
| Two models | run A's latest pass uses model M1, run B's uses M2 | two charts, each with its own name, version, totals and dates | No error expected |
| No sentiment | no run has a sentiment pass, or every row was purged | no chart; "No sentiment results yet" | No error expected |
| Other owner | another owner's project has rows | never counted | 404 on a foreign project, as today |

</frozen-after-approval>

## Code Map

- `src/api/core/views.py`:
  - `ResultsSummaryView.get` (US-027/US-029) already resolves the project, applies `parse_results_filters` and builds `video_ids`. Reuse it as-is.
  - `CollectionRunSentimentView.get_sentiment_run` shows the latest-pass rule: the newest `ProcessingRun` of a collection run whose `summary_payload` has `model_name`, ordered by `-created_at, -id`.
  - Do not change the run sentiment endpoint.
- `src/api/core/models.py`: read-only. The relevant fields are `CommentSentiment` (`processing_run`, `comment`, `model_name`, `model_version`, `sentiment_label`), `ProcessingRun.collection_run` and `CollectionRunComment.discovered_at`. `CommentSentiment.SentimentLabel.values` gives the label order.
- `src/api/core/tests.py`: `ResultsSummaryApiTests` (US-027/029) and `SentimentResultsApiTests` (US-026/030) have the fixtures for runs, passes and sentiment rows.
- `src/ui/src/apiClient.ts`: `ResultsSummary`, `isResultsSummary` and `getResultsSummary`. Extend the type with `sentiment` and guard it; `tests/resultsSummaryApi.test.ts` holds the guard tests.
- `src/ui/src/sentimentFormat.ts`: home for the pure chart helper. `SENTIMENT_LABELS` in `apiClient.ts` gives the order.
- `src/ui/src/App.tsx`: the Results panel article (`summary-card`), below the counts and the "Data collected between" line. `formatTimestamp` gives the date text.
- `src/ui/src/App.css`: `.summary-card` and `.run-summary` styles. Add a small `.sentiment-chart` block.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/views.py` -- in `ResultsSummaryView.get`, compute `sentiment` over this project's runs' latest passes and `video_ids` (Always rules). Python counting over `values_list` is fine at the current per-run caps; avoid `DISTINCT ON`, which SQLite lacks.
- [x] `src/api/core/tests.py` -- in `ResultsSummaryApiTests`, one test per I/O row plus one with a video filter, on Compose PostgreSQL.
- [x] `src/ui/src/apiClient.ts` -- the distribution type, the guard and its tests.
- [x] `src/ui/src/sentimentFormat.ts` -- `sentimentDistribution(labels)`, returning rows of `{label, count, percent, width}`, with tests for zero total, rounding and order.
- [x] `src/ui/src/App.tsx` and `src/ui/src/App.css` -- render one chart per model with its dates and the empty state.

**Acceptance Criteria:**
- Given the stale-pass test, when every pass counts instead of the latest, then the test fails.
- Given the shared-comment test, when rows are counted instead of distinct comments, then the total is 2 and the test fails.
- Given an all-zero distribution, when it is rendered, then no division by zero occurs: every percent is 0.0% and every bar is empty.

## Implementation Notes

- Baselines: API `8314d6dbf997226e0a415cff05a5d1ef6417e0a3` (frontmatter), UI `fde08574b624ae733ff06c522c32644749b08b52`, thesis `800c5cc90ee3300a6a5a90aa841599b35b8659c7`. Both app repos are on `feature/US-028`.
- `sentiment_distributions(project, video_ids)` in `views.py`, called from `ResultsSummaryView.get`. Latest pass per run in Python (passes ordered by run, `-created_at`, `-id`; the first per run wins), no `DISTINCT ON`. Rows outside the pass's reported model are skipped; per model, each comment keeps the label of the pass with the highest `(created_at, id)`. The dates come from the counted comments' `CollectionRunComment.discovered_at` on this project's runs, so they can differ from the card's run-video "Data collected between" line.
- UI: `SentimentDistribution` + a private `isSentimentDistribution` guard; pure `sentimentDistribution(labels)` in `sentimentFormat.ts`; one `<section className="sentiment-chart">` per model after the card's date line, with "No sentiment results yet" for `[]`. The bar is `aria-hidden`; the label, count and percent are text.
- Mutation checks (implementer): counting every pass fails the stale-pass test; counting rows fails the shared-comment test (total 2); dropping the model check fails the stray-row test; oldest-wins fails the shared-comment test; removing the zero guard gives `NaN%` in the all-zero test.
- Review patch (pass 1) applied: the date-scoping test above. Re-verified: backend 337 OK on PostgreSQL, migrations clean; UI 88 pass, build and lint clean.

- Orchestrator check: backend 337 OK on PostgreSQL, migrations clean; UI 88 pass, build and lint clean. All 7 matrix rows plus the video and date filters are covered by `ResultsSummaryApiTests` tests that ran.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 1, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| No test fails when `collection_run__project=project` is dropped from the date query in `sentiment_distributions`, so a counted comment's link to another owner's or project's run could widen "Comments collected between" | low | patch | Confirmed: the other-owner test only asserts `[]` and the shared-comment test links both runs to this project. `test_sentiment_counts_one_models_labels_with_dates` now gives counted comments foreign-owner and sibling-project links 30 h outside the range on both sides; it fails with the filter removed. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: No changes detected.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass.

**Manual checks:**
- Seed a sentiment pass with page 31's snippet, open the project, and check that the chart shows the counts with percentages and the dates. Apply a video filter and check that the chart narrows.
