# 38 - Export raw payloads, sentiment and metrics

Story: US-032, Export raw payloads, sentiment and metrics as JSON or CSV.

Status note: this document describes the US-032 implementation **after** the code review of 2026-10-09 and the fixes that followed it.

## What this story added

Two more links in the **Results** panel's **Export** group (page 36):

- **Dataset JSON:** one file with everything a researcher needs to continue outside the app:
  - the raw YouTube payloads of the videos, channels and comments;
  - the statistics snapshots;
  - the sentiment results;
  - the processing reports;
  - the results summary.
- **Sentiment CSV:** the same sentiment results as flat rows, for a spreadsheet or pandas.

A second hint line under the links says what the JSON holds and how to load it.

Behind the links are two API endpoints:

```text
GET /api/projects/<project_id>/export/dataset.json
GET /api/projects/<project_id>/export/sentiment.csv
```

The files are named like `dataset-<project id>-2026-10-09.json` and `sentiment-<project id>-2026-10-09.csv`.

## Why this matters

Page 36 exports flat columns. The analysis in a thesis also needs:
- the comments with their sentiment labels;
- the exact data YouTube sent, to check a column or recompute a value;
- the processing reports that say how the text was cleaned and which model labelled it.

All of it falls under the 30-day policy (page 26), so every record in the file carries its own dates, as in page 36.

## Key concept: a documented, versioned format

The JSON file names its own format:

```json
{"format": "opentube-insights-dataset", "format_version": 1, ...}
```

The full schema, every key with its type and meaning, is in `src/api/README.md` under "Dataset export". The top level is:

| key | what it holds |
| :-- | :-- |
| `project`, `exported_at`, `retention_days` | which project, when, and the retention period (30) |
| `videos`, `channels`, `comments` | one record per row, with its `raw_payload` exactly as YouTube returned it |
| `statistics_snapshots` | view, like and comment counts per video per run, with `raw_statistics` |
| `sentiment` | one row per comment classified by each run's latest sentiment pass |
| `processing_runs` | every cleaning and sentiment report, verbatim |
| `summary` | exactly what `GET .../results/summary/` returns without filters |

`format_version` goes up when a key changes meaning or disappears. A script reading the file can check it and stop, rather than misread a changed file.

## Key concept: dates on every record

| record | `collected_at` | `delete_by` |
| :-- | :-- | :-- |
| video, channel, comment | `last_fetched_at` | `collected_at` + 30 days |
| statistics snapshot | none; `captured_at` instead | `captured_at` + 30 days |
| sentiment row | its comment's | its comment's |
| processing report | `created_at` | `null` |
| summary | none | none |

Why:
- **Sentiment rows** take their comment's dates because the purge deletes a sentiment row together with its comment.
- **Processing reports** hold counts only, no YouTube data, and the purge keeps them (page 26). So `delete_by` is `null`: present, but empty.
- **The summary** is computed at export time from whatever is left, so it has no dates of its own.

As in page 36, the 30 is `RETENTION_DAYS` imported from `core/purge.py`, never written again.

The review corrected what `delete_by` means. It is the date the data **must be deleted by**, not the moment the purge deletes it. The purge can remove a comment or snapshot **earlier**: it deletes a video once the video itself is old enough, and that video's comments and snapshots go with it. The README, both hint lines and page 36 now say so.

## Key concept: the latest pass, one model

A run can be classified more than once, for example after changing `SENTIMENT_MODEL`. The export follows the rule from page 31:

1. For each run, take the newest sentiment pass: the newest `ProcessingRun` whose report names a `model_name`.
2. From that pass, keep only the rows whose model name and version match the report.

So the file never mixes an old pass with a new one, or one model with another. If two runs classified the same comment, it appears once per run; each row says which `collection_run_id` it belongs to.

This rule now lives in one helper, `latest_sentiment_passes(project)`, which the results chart (page 35) and the export both use.

## Key concept: the summary cannot drift

The dataset's `summary` must equal what the Results card shows. Rather than compute it twice, the body of `ResultsSummaryView` moved into a function, `results_summary(project, filters)`. The endpoint calls it with the request's filters, and the export calls it with none. A test compares the two responses.

## Key concept: numbers are not escaped

Page 36 put a `'` before any cell starting with `-`, to stop spreadsheets running it as a formula. Applied to a sentiment score, that turned `-0.500000` into the text `'-0.500000`, and pandas read the whole column as text.

The review caught this. `csv_cell` now escapes **text** only. Numbers (`int`, `float`, `Decimal`) are written as they are, since a number cannot be a formula. This also changes the CSVs from page 36: their numeric columns, such as view counts, were never negative, so no output there actually changes.

## File-by-file explanation

### `src/api/core/views.py` and `src/api/core/urls.py`

- **New helpers:**
  - `latest_sentiment_passes(project)`: run id to its newest sentiment pass and report;
  - `results_summary(project, filters)`: the summary body, shared with `ResultsSummaryView`;
  - `linked_records(project)`: this project's videos, channels and comments, each once, through its run links. The page 36 CSVs use it too;
  - `sentiment_export_rows(project)`: the sentiment rows with their comment's dates.
- **`ProjectDatasetExportView`:** builds the JSON document. `DATASET_FORMAT`, `DATASET_FORMAT_VERSION` and `DATASET_FIELDS` name the format and the fields of each record.
- **`ProjectCsvExportView`:** new kind `sentiment`, with its columns in `EXPORT_COLUMNS`.
- **`csv_cell`:** no longer escapes numbers.
- **Routes:** `project-export-dataset` and `project-export-sentiment`.

### `src/api/core/tests.py`

`DatasetExportApiTests`, one test per case:
- raw payloads, each record once, with both dates;
- the latest pass only, without a stray row of another version or another model;
- the reports verbatim, and the summary equal to the endpoint's body;
- a project with no runs: the format header and empty lists, and a CSV with the header only;
- purged data: only reports and the summary remain;
- another owner's or a missing project: 404.

`CsvCellTests.test_numbers_are_never_escaped` is new.

### `src/api/README.md`

The "Dataset export" section with the full schema, and the corrected `delete_by` and escaping notes in the CSV section.

### `src/ui/src/apiClient.ts` and `src/ui/src/App.tsx`

`ExportKind` gains `sentiment` and `dataset`. `exportUrl` gives `dataset` a `.json` extension and every other kind `.csv`. The two links are plain `<a href download>` elements, as in page 36.

## How the pieces connect

```text
Results panel -> Export
   Dataset JSON -> ProjectDatasetExportView
        linked_records(P)          -> videos, channels, comments (+ raw_payload, dates)
        P's runs                   -> statistics_snapshots, processing_runs
        latest_sentiment_passes(P) -> sentiment_export_rows(P) -> sentiment
        results_summary(P, {})     -> summary  (same function as GET .../results/summary/)
     <- dataset-P-YYYY-MM-DD.json
   Sentiment CSV -> ProjectCsvExportView(kind="sentiment")
        sentiment_export_rows(P) -> BOM + header + csv_cell rows
     <- sentiment-P-YYYY-MM-DD.csv
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py makemigrations --check --dry-run
curl -sS -OJ http://127.0.0.1:8000/api/projects/<project-uuid>/export/dataset.json
cd ../ui
npm test
npm run build
npm run lint
```

Passing looks like:
- `OK` (358 tests);
- `No changes detected`;
- `pass 89`, a finished build and no lint output.

The `curl` command saves `dataset-<project-uuid>-<date>.json` in the current folder.

## How to test manually

1. `cd src && ./run-local.sh`, open `http://localhost:5173/`, and pick a project with collected data. For sentiment rows, seed a sentiment pass first with the recipe on page 31.

2. Click **Dataset JSON**, then **Sentiment CSV**. Both download.

3. In Python:

   ```python
   import json
   import pandas as pd

   data = json.load(open("dataset-<project-uuid>-<date>.json"))
   print(data["format"], data["format_version"], len(data["comments"]))
   print(data["summary"]["comments"])
   df = pd.read_csv("sentiment-<project-uuid>-<date>.csv", encoding="utf-8-sig")
   print(df["sentiment_score"].dtype)
   ```

   - The first line prints `opentube-insights-dataset 1` and the number of comments.
   - The second matches the Results card's comment count.
   - The dtype is `float64`, not `object`; `object` would mean the scores were escaped as text.

## Common errors

- **`summary` differs from the Results card.** The card follows the filters above it; the export never does. Clear the filters to compare.

- **Fewer sentiment rows than comments.** Only each run's latest pass counts, and comments without text are skipped by the classifier (its report's `skipped_no_text`).

- **`json.load` fails with a `UnicodeDecodeError` on Windows.** Open the file with `encoding="utf-8"`. The JSON file has no BOM; only the CSV files do.

## Known gaps

- The document is built in memory (a `ponytail:` comment marks it). A very large project would need a streamed response.
- No filtered exports; both files cover the whole project, as in page 36.
- No zip of all files and no background export job; each link is one request.
