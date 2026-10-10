---
title: 'Export raw payloads, sentiment and metrics as JSON or CSV'
type: 'feature'
ticket: '2'
created: '2026-10-09'
status: 'done'
baseline_revision: 'e2b10aeb25a3d4ef8e64ccc62919646a9585dadb'
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

**Problem:** US-031 exports videos, channels and logs as flat columns. A researcher still cannot take out the raw API payloads, the comments with their sentiment results, or the derived metrics, so the analysis cannot continue outside the app within the 30-day window (US-032).

**Approach:** Add a project-level export of those three, in a documented format (shape in Decisions). Every record states its collection date and the date it must be deleted, from the same rules as US-031.

## Boundaries & Constraints

**Always:**
- **Content:**
  - **Raw payloads:** each video's, channel's and comment's `raw_payload`, and each statistics snapshot's `raw_statistics`.
  - **Sentiment:** for every comment of this project's runs, the rows of each run's **latest** sentiment pass whose model equals that pass's report (US-026's rule). Each row carries its comment, `collection_run_id`, `processing_run_id`, `model_name`, `model_version`, label, score, confidence and language.
  - **Derived metrics:**
    - every `ProcessingRun` report (`summary_payload`) of the project's runs;
    - the statistics snapshots (view, like and comment counts per video per run);
    - the results summary counts and the per-model sentiment distribution, exactly as `GET .../results/summary/` returns them unfiltered.
- **Scoping:** owner and project as every export (US-031). Shared rows go through this project's run links and appear once.
- **Dates on every record:**
  - comments, videos and channels: `collected_at` = `last_fetched_at`, and `delete_by` = `last_fetched_at + RETENTION_DAYS`;
  - snapshots: `captured_at`, and `delete_by` = `captured_at + RETENTION_DAYS`;
  - sentiment rows: the dates of their comment, because the purge cascades from it;
  - processing reports and the summary: no `delete_by`, because the purge keeps them (US-040). The format says so explicitly.

  `RETENTION_DAYS` is imported, never restated.
- **Documented format:** the schema (every key, its type and its meaning) is written in `src/api/README.md` and on the story page. The file itself names the format and its version.
- **CSV safety:** any CSV output reuses `csv_cell` and the BOM from US-031.
- **UI:** links in the Results panel's Export group, with one hint line. They reuse `exportUrl`.
- Tests parse the output and assert the scoping, the dates, the latest-pass rule, purge behaviour and the 404. No network. Validated on Compose PostgreSQL.

**Decisions** (approved by the human on 2026-10-09):
- **Shape:** two exports.
  - **`GET /api/projects/<p>/export/dataset.json`** is one JSON document:

    ```text
    {"format": "opentube-insights-dataset", "format_version": 1,
     "project", "exported_at", "retention_days",
     "videos", "channels", "comments", "statistics_snapshots",
     "sentiment", "processing_runs", "summary"}
    ```

    It is served as an `application/json` attachment named `dataset-<project id>-<UTC date>.json`. Payloads are nested JSON. Every record carries `collected_at`/`delete_by` (snapshots: `captured_at`/`delete_by`), with `delete_by` null where the purge keeps the record.
  - **`GET /api/projects/<p>/export/sentiment.csv`** gives the same sentiment rows flat, through the US-031 CSV view, with the comment's `youtube_comment_id`, `collected_at` and `delete_by`.

**Never:**
- No API keys, request headers or anything not already stored.
- No US-029 filters.
- No re-running sentiment.
- No server-side files, zips or background jobs.
- No migrations and no new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Raw payloads | 1 video and 1 channel with payloads, 2 comments, 1 snapshot in this project; another project's video | exactly this project's records, each with its stored payload and both dates | No error expected |
| Latest pass | a run with an older and a newer sentiment pass, and a stray row of another model | only the newer pass's rows of its reported model | No error expected |
| Metrics | a normalization and a sentiment report; summary counts | both reports verbatim with no `delete_by`; the summary equals the summary endpoint's body | No error expected |
| Empty | a project with no runs | `dataset.json` with the format header and empty lists; `sentiment.csv` header only | No error expected |
| Purged | the project's data purged | no payloads, comments, snapshots or sentiment; reports and summary still present | No error expected |
| Foreign project | another owner's project | no data | 404 |

</frozen-after-approval>

## Code Map

- `src/api/core/views.py`:
  - `ProjectCsvExportView`, `EXPORT_COLUMNS`, `csv_cell` and `FORMULA_PREFIXES` (US-031) for any CSV output, the BOM and the filename pattern;
  - `ResultsSummaryView.get` and `sentiment_distributions` (US-028) for the summary body; extract a helper both use rather than calling the view;
  - `CollectionRunSentimentView.get_sentiment_run` for the latest-pass rule (newest `ProcessingRun` with `summary_payload__has_key="model_name"`).
- `src/api/core/purge.py`: `RETENTION_DAYS`.
- `src/api/core/urls.py`: new routes beside `project-export-*`.
- `src/api/core/models.py`: read-only. `YouTubeComment`, `VideoStatisticsSnapshot`, `CommentSentiment` and `ProcessingRun`.
- `src/api/core/tests.py`: `CsvExportApiTests` (US-031) and `ResultsSummaryApiTests` hold the fixtures. `FakeClassifier` and the sentiment helpers are around `AnalyzeCommentsTests`.
- `src/api/README.md`: the export section from US-031. Add the schema.
- `src/ui/src/apiClient.ts`: extend `ExportKind` and `exportUrl`.
- `src/ui/src/App.tsx`: the `results-export` group.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/views.py` + `core/urls.py` -- `dataset.json` (a small view) and `sentiment` as a new `ProjectCsvExportView` kind.
- [x] `src/api/core/tests.py` -- one test per I/O row.
- [x] `src/api/README.md` -- the documented schema.
- [x] `src/ui/src/apiClient.ts` + test, `src/ui/src/App.tsx` -- the links and hint.

**Acceptance Criteria:**
- Given the latest-pass test, when every pass's rows are exported, then it fails.
- Given the raw-payload test, when `delete_by` uses a number other than `RETENTION_DAYS`, then it fails.
- Given the metrics test, when the exported summary is computed separately from the summary endpoint, then any drift between the two fails the test.

## Implementation Notes

- Baselines: API `e2b10aeb25a3d4ef8e64ccc62919646a9585dadb` (frontmatter), UI `55a71ff46c2c36600d3b29a207b2b83980e5db04`, thesis `d6a17ceb67729b5ed308e2beff8bc04121c47358`. Both app repos are on `feature/US-032`.
- Extracted `latest_sentiment_passes(project)` (now used by `sentiment_distributions`) and `results_summary(project, filters)` (used by `ResultsSummaryView` and the dataset, so they cannot drift). Added `linked_records(project)` (videos, channels, comments once, through `pk__in` subqueries; the US-031 CSV now uses it instead of `.distinct()`) and `sentiment_export_rows(project)`.
- `sentiment` is a new `ProjectCsvExportView` kind. `ProjectDatasetExportView` uses the JSON renderer only and serves the documented document; the README has the schema.
- Choices left open by the plan: a processing run's `collected_at` is its `created_at`; the summary is the endpoint body verbatim, with no `delete_by` key; JSON scores are numbers, CSV scores as stored (`0.500000`); a comment classified by two runs gives one row per run (each row carries `collection_run_id`); the document is built in memory (`ponytail:` comment).
- Acceptance mutations (implementer): exporting every pass, `days=31`, and a changed summary each fail their test.
- Review patches (pass 1) applied, see the triage log. Re-verified: backend 358 OK on PostgreSQL, migrations clean; UI 89 pass, build and lint clean.

- Orchestrator check: backend 357 OK on PostgreSQL with all six `DatasetExportApiTests` run, migrations clean; UI 89 pass, build and lint clean. All 6 matrix rows are covered.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 4, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `csv_cell` escapes numbers like text, so every negative `sentiment_score` in sentiment.csv exports as `'-0.500000` and pandas reads the column as text | medium | patch | Confirmed (`csv_cell(Decimal("-0.500000"))` gave `'-0.500000`). Only text cells are escaped now; int, float and Decimal are written as is (a number cannot run as a formula). This narrows US-031's approved "every cell" wording to text cells, reported to the human. `test_numbers_are_never_escaped`; the latest-pass test uses a negative score. |
| The empty-project test always had a run, so "a project with no runs" was never exported | low | patch | Confirmed. The test exports a fresh project with no runs, for both files, and asserts `summary.runs == 0`. |
| The latest-pass test's only stray row differs in `model_version`, so the `model_name` half of the filter was unchecked | low | patch | Confirmed. A stray `m2`/`1.0` row is excluded; fails without the `model_name` condition. |
| `delete_by` was described as the instant after which the purge deletes the record, but comments and snapshots can go earlier by cascade with their video | low | patch | Confirmed in `purge.py`. README (US-031 and dataset paragraphs) and the UI hint now say `delete_by` is the date the data must be deleted by, and the purge may remove it earlier with its video. |
| The export hints say the dataset holds "this summary" (it is always unfiltered), put `utf-8-sig` advice over the JSON link, and say reports "have no `delete_by`" (it is null) | low | patch | Confirmed. Hints corrected: unfiltered summary, `json.load` for the JSON, `utf-8-sig` for the CSVs, reports' `delete_by` null. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: No changes detected.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass.

**Manual checks:**
- With collected data and a seeded sentiment pass (page 31), download each export and load it: `json.load` for the dataset, and `pd.read_csv(..., encoding="utf-8-sig")` for the CSV.
