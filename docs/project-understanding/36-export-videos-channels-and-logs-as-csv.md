# 36 - Export videos, channels and logs as CSV

Story: US-031, Export videos, channels and logs as CSV.

Status note: this document describes the US-031 implementation **after** the code review of 2026-10-09 and the fixes that followed it.

## What this story added

The **Results** panel has an **Export** group with three download links for the active project:

- **Videos CSV:** every video this project's runs found, once each.
- **Channels CSV:** the channels of those videos.
- **Request logs CSV:** every YouTube request this project's runs made.

Under the links, one line explains the date columns, the escaping, and that the exports ignore the filters above them.

Behind the links are three API endpoints:

```text
GET /api/projects/<project_id>/export/videos.csv
GET /api/projects/<project_id>/export/channels.csv
GET /api/projects/<project_id>/export/request-logs.csv
```

Each answers with a file named like `videos-<project id>-2026-10-09.csv`, dated with the export day in UTC.

## Why this matters

A researcher needs to cite the dataset and continue the analysis in pandas, R or a spreadsheet. The YouTube API policy also limits how long the data may be kept (page 26), and that limit follows the data out of the app. So every exported row says when its data was collected and when it must be deleted.

## Key concept: two dates in every row

Every file ends with two columns:

| file | `collected_at` | `delete_by` |
| :-- | :-- | :-- |
| videos, channels | `last_fetched_at`: when YouTube last sent this data | `last_fetched_at` + 30 days |
| request logs | `started_at`: when the request was made | empty |

`delete_by` uses the purge's own constant, `RETENTION_DAYS`, imported from `core/purge.py` rather than written as `30` again, so the export and the purge can never disagree. The purge deletes a row once `delete_by` has **passed**. Its cutoff is strict, which is why the purged test runs the purge one microsecond after `delete_by`.

Request logs have no deletion date because the purge keeps them. They record what the app asked YouTube and what it cost, not YouTube's content (page 24).

## Key concept: shared rows, scoped exports

Videos and channels are shared across projects (page 25). A video found by two of this project's runs, or also by another project, is one row in the database. The export therefore:

- selects only videos linked by **this project's** runs;
- lists each video **once** (`.distinct()`; a test fails without it);
- sorts videos and channels by title, then id;
- sorts logs by run, oldest run first, then by request number. The review caught that sorting "by run" silently used the run's creation time instead of its id, so two runs created at the same moment had their logs interleaved. It now sorts by the run id itself.

Another owner's project, or a project that does not exist, is a `404`, as on every project endpoint.

The columns are each model's own fields, with no raw payloads, comments, sentiment or statistics snapshots; those are US-032. Videos add `youtube_channel_id`, and logs add `collection_run_id`. Timestamps are ISO 8601 in UTC (`2026-10-01T12:00:00+00:00`), and JSON fields such as `tags` and `request_params` are written as JSON text.

## Key concept: spreadsheet-safe CSV

Titles and descriptions come from YouTube, so they are untrusted text. A spreadsheet runs a cell that starts with `=`, `+`, `-` or `@` as a **formula**, so a video titled `=HYPERLINK("…")` could act when the file is opened. This is called CSV injection.

As you decided, the export follows the OWASP advice. `csv_cell` puts a `'` in front of any cell that starts with `=`, `+`, `-`, `@`, a tab or a carriage return. That has two costs:

- **Text changes:** a title `-5 reasons` exports as `'-5 reasons`.
- **Identifiers change too.** A YouTube video id can start with `-` (about 1 in 64 do), and it gets the same `'`. Strip a leading `'` before joining an export on `youtube_video_id`. The review found that nothing said this, so the UI line and the README now do.

The file also starts with a UTF-8 **byte-order mark** (BOM), an invisible marker that makes Excel read accents and emoji correctly. pandas then needs `pd.read_csv(path, encoding="utf-8-sig")`. With plain `utf-8`, the first column name would read `﻿id`.

## File-by-file explanation

### `src/api/core/views.py` and `src/api/core/urls.py`

- `EXPORT_COLUMNS`: each file's columns, by model field name.
- `csv_cell(value)`: one pure function that turns any value into safe text. It renders empty for None, ISO 8601 UTC for datetimes and JSON for lists and dicts, then adds the `'` prefix.
- `ProjectCsvExportView`: one view, configured per route with `as_view(kind=...)`. It writes the BOM, the header and one row per record with Python's `csv` module.
- Three routes: `project-export-videos`, `project-export-channels` and `project-export-request-logs`.

### `src/api/core/tests.py`

- `CsvCellTests`: the escaping and value rendering on their own.
- `CsvExportApiTests` reads every response the way a researcher would, with `csv.DictReader` after decoding `utf-8-sig`, and checks the exact header and the BOM. It has a test for each case:
  - videos, with the filename and both dates
  - channels and their order
  - log order, including runs created together
  - an empty project
  - another owner's or a missing project
  - Unicode titles
  - formula cells
  - purged data

### `src/api/README.md`

A `curl -OJ` example and the notes on dates, the BOM and escaping.

### `src/ui/src/apiClient.ts`, `src/ui/tests/resultsSummaryApi.test.ts`, `src/ui/src/App.tsx` and `src/ui/src/App.css`

`exportUrl(projectId, kind)` builds each link through `buildApiUrl`, so the configured API base is respected. The links are plain `<a href download>` elements: the browser does the download, so no JavaScript fetch, Blob or library is needed.

## How the pieces connect

```text
Results panel -> Export
   <a href="/api/projects/P/export/videos.csv" download>
        '-- ProjectCsvExportView(kind="videos")
               P's run links -> distinct videos, by title
               BOM + header + rows
               each cell -> csv_cell (ISO UTC, JSON, ' before = + - @ \t \r)
               + collected_at = last_fetched_at
               + delete_by    = last_fetched_at + RETENTION_DAYS
        <- videos-P-YYYY-MM-DD.csv
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
curl -sS -OJ http://127.0.0.1:8000/api/projects/<project-uuid>/export/videos.csv
cd ../ui
npm test
npm run build
npm run lint
```

Passing looks like `OK` (348 tests), `pass 89`, a finished build and no lint output. The `curl` command saves `videos-<project-uuid>-<date>.csv` in the current folder.

## How to test manually

1. `cd src && ./run-local.sh`, open `http://localhost:5173/`, and pick a project with collected data.

2. Click **Videos CSV**. The browser downloads the file. Opened in a spreadsheet, it shows one row per video, accents intact, and the last two columns 30 days apart.

3. Click **Request logs CSV**. Its `delete_by` column is empty.

4. In Python:

   ```python
   import pandas as pd
   df = pd.read_csv("videos-<project-uuid>-<date>.csv", encoding="utf-8-sig")
   df["youtube_video_id"] = df["youtube_video_id"].str.removeprefix("'")
   ```

## Common errors

- **The first column is called `﻿id` (or `ï»¿id`).** The file was read as plain UTF-8. Use `encoding="utf-8-sig"`.

- **A title or id starts with `'`.** That is the formula escaping. Strip one leading `'` if you need the original text.

- **The export has more rows than the filtered card.** The exports ignore the date and video filters; they cover the whole project.

- **Videos and channels have only a header.** Nothing is collected yet, or the data was purged after 30 days (page 26). The logs export still has rows.

- **`406 Not Acceptable`.** The client asked only for `text/csv` in its `Accept` header, which the API's content negotiation refuses. Browsers, curl and pandas do not do that.

## Known gaps

- No filtered exports, and no JSON. Raw payloads, comments, sentiment and metrics are US-032.

- The escaping applies to every cell, identifiers included. Exempting the id columns would need a new decision.
