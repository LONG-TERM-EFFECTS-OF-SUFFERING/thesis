# 16 - Show request logs for each collection run

Story: US-014, Show request logs for each collection run.

Status note: this document describes the US-014 implementation **after** the code review of 2026-10-07 and the fixes that followed it.

## What this story added

Request logs (US-013) and run totals (US-012) were only visible in the Django admin. This story puts them in the app:

- **API**: two read-only endpoints.
  - `GET /api/projects/<project_id>/runs/` lists a project's runs, newest first.
  - `GET /api/projects/<project_id>/runs/<run_id>/` returns one run with its request logs.

- **UI**: a third panel, **Collection runs**, below Projects and Saved queries.
  - A table of the active project's runs: created, query, status, requests, quota, videos.
  - A **Refresh** button.
  - Clicking a run shows its request logs in a second table: #, endpoint, page token sent, HTTP status, items, quota, started, error. Failed requests are highlighted. A run with no requests yet says so.

## Why this matters

The thesis promises that a reader can inspect the evidence behind a dataset. Until now that evidence existed only in the database and the admin. Now a researcher can open a run and see, request by request, what the app asked YouTube, what came back and what it cost.

## Key concept: list without logs, detail with logs

The two endpoints return different amounts of data on purpose:

- the **list** returns each run's status and totals, but no logs. Loading every run's logs just to draw one table would be wasted work.

- the **detail** nests the run's `request_logs` in `request_sequence` order. A run makes one `search.list` call per 50 videos, so even a 500-video run has about 10 log rows. That is small enough to send in one response, with no separate logs endpoint and no pagination.

Both views are Django REST Framework generic views (`ListAPIView` and `RetrieveAPIView`), which only allow GET, so any write is a `405`. Both get their runs through `ProjectOwnerMixin.get_project()`. A run from another owner's project, or from another project, is therefore a `404`, the same answer as a run that does not exist.

The serializers expose only what the log already stores. There are no response bodies and no API key, and YouTube IDs were already replaced by counts when the log was written (US-013).

## Key concept: why there is a Refresh button

Runs are collected outside the web app, by `manage.py collect_runs` (US-015). The browser does not know when that finishes, so the panel does not update by itself. Refresh reloads the runs list and, if a run's logs are open, reloads them too. Without the second part, a run that was `pending` when you opened it would keep showing "No requests yet" after collection finished. The code review caught that.

Polling (asking the server every few seconds) was left out on purpose: it adds timers and cleanup for a local research tool where a button is enough.

## Key concept: late responses (the AGENTS.md pitfall)

A request started for project A can come back after you have switched to project B. If its result were written to the screen, you would see A's runs under B. This bug has hit this project twice before, so every fetch in the panel follows the same rule:

1. each fetch gets its own `AbortController`, kept in a `useRef`. Starting a new fetch aborts the previous one.

2. before writing state, the code checks that its controller is still the current one (`controllerRef.current === controller`). An older request that finished late is ignored.

3. the state carries the `projectId` it belongs to, and the panel only draws state for the active project.

The list-merging logic lives in `src/ui/src/collectionRunState.ts` as pure functions, so it can be tested without a browser:

- `mergeLoadedRuns` ignores a response for another project, and keeps a run started while the request was in flight.

- `prependRun` puts a just-started run at the top without duplicating it. If the list is showing an error it leaves the error alone, so the screen never pretends a failed list is complete (a review fix).

- `isFailedLog` decides which log rows are highlighted: a stored error message, or an HTTP status of 400 or higher.

## File-by-file explanation

### `src/api/core/serializers.py`

- `CollectionRunSerializer` gains `saved_query_name`, which is empty once the query is deleted.

- `ApiRequestLogSerializer` returns every log field except the run link.

- `CollectionRunDetailSerializer` is the run serializer plus the nested `request_logs`.

### `src/api/core/views.py` and `src/api/core/urls.py`

`CollectionRunListView` and `CollectionRunDetailView`, routed as `project-run-list` and `project-run-detail`.

### `src/api/core/tests.py`

`CollectionRunReadApiTests` covers the list order without logs, the detail with logs in order (created out of order on purpose), a deleted query, foreign and unknown runs (`404`) and writes (`405`).

### `src/ui/src/apiClient.ts`

The `ApiRequestLog` and `CollectionRunDetail` types, with guards that check the JSON shape before the UI trusts it, plus the fetchers `listCollectionRuns` and `getCollectionRun`.

### `src/ui/src/collectionRunState.ts`

The pure helpers described above.

### `src/ui/src/App.tsx` and `src/ui/src/App.css`

The panel, the two tables, Refresh, and the start button's hook into `prependRun`. CSS styles the tables and lets wide tables scroll sideways.

### `src/ui/tests/collectionRunApi.test.ts` and `src/ui/tests/collectionRunState.test.ts`

These test the guards and fetchers (with `fetch` faked) and the three helpers.

## How the pieces connect

```text
App (active project P)
  |-- useEffect on P / Refresh --> listCollectionRuns(P)
  |        GET /api/projects/P/runs/  --> CollectionRunListView (runs of get_project())
  |        --> mergeLoadedRuns(state, P, runs)      (ignored if P is no longer active)
  |-- "Start run" on a query card --> prependRun(state, P, run)
  '-- click a run R / Refresh with R open --> getCollectionRun(P, R)
           GET /api/projects/P/runs/R/ --> CollectionRunDetailView (+ request_logs)
           --> logs table, failed rows marked by isFailedLog
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
cd ../ui
npm test
npm run build
npm run lint
```

Passing looks like `OK` (153 tests), `pass 59`, a finished build and no lint output. The two curl commands for the new endpoints are in [commands.md](commands.md), under Collection runs.

## How to test manually

1. Run the app and pick a project with a saved query. The Collection runs panel lists its runs, or says "No runs yet".

2. Click **Start run** on a query card. The new run appears at the top as `pending`.

3. Click the run. Its logs area says "No requests yet".

4. Run `venv/bin/python manage.py collect_runs` from `src/api` (this needs a real `YOUTUBE_API_KEY`, or use the fake-transport shell recipe on page 12).

5. Click **Refresh**. The run's row and its open logs both update: status `completed`, one row per `search.list` page.

6. Open `/admin/` → Api request logs and compare. Each table row matches one admin row.

If you are logged into `/admin/`, open it on `127.0.0.1` and the UI on `localhost`. Otherwise the start request fails with a `403` (see page 11).

## Common errors

- **The run stays `pending` after Refresh.** Nobody ran `collect_runs` yet.

- **`404` when opening a run.** The run belongs to another project or owner, or was deleted along with its project.

- **"No requests yet" on a completed run.** The run found nothing to request. With a valid key this should not happen, so check the run's `error_message` in the list.

## Known gaps

- On the very first page load, the panel briefly says "Choose a project" while the runs load. The Saved queries panel does the same, and the review left both alone.

- The panel has no automated render test (no React test harness yet), so the manual check above is how the tables themselves are verified.

- No discovery summary or video list yet. That is US-016.
