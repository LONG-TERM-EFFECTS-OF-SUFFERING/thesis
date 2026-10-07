# 25 - Show results summary counts and card

Story: US-027, Show results summary counts and card.

Status note: this document describes the US-027 implementation **after** the code review of 2026-10-07 and the fixes that followed it. It is the first story of the Results visualization and analysis epic.

## What this story added

Until now, seeing how much a project had collected meant opening each run, or the admin. This story adds a **Results** panel with a summary card for the active project:

| on the card | meaning |
| :-- | :-- |
| project name and status | which project the numbers describe |
| Runs | collection runs of this project |
| Videos | distinct videos this project's runs found |
| Channels | distinct channels of those videos |
| Comments, Replies | top-level comments and replies this project's runs collected |
| Statistics snapshots | snapshots this project's runs recorded |
| Data collected between X and Y | the first and last time this project's runs found a video |

Behind it is one read-only endpoint: `GET /api/projects/<project_id>/results/summary/`.

The card reloads when you switch project, click **Refresh** in the runs panel, or start a run.

## Why this matters

A researcher needs to know the size and coverage of a dataset before interpreting it: how many videos, how many comments, and from when. The card answers that at a glance, and the later results stories build on it (the sentiment chart in US-028, filters in US-029 and US-030).

## Key concept: counting in the database

All numbers are computed by PostgreSQL in a few queries, using Django aggregates:

- `Count("id", distinct=True)`: a video found by **two** runs of the project counts **once**.
- `Count(..., filter=Q(comment_level=...))`: comments and replies are counted in the same query, split by level.
- `Min` / `Max`: the date range.

Python never loads the rows to count them, so the card stays fast as the data grows.

## Key concept: shared rows, scoped counts

Videos, channels and comments are **shared**. If two projects, or two researchers, collect the same video, there is one `youtube_videos` row. So "this project's videos" cannot mean "all videos", and it cannot mean "everything attached to those videos" either:

- **videos and channels** are counted through this project's run-video links;
- **comments, replies and snapshots** are counted through **this project's runs**, never through the videos. Otherwise another researcher's comments on a shared video would appear in your numbers.

Tests check both: another project of yours is not counted, and another owner who collected the same video is not counted.

## Key concept: which date is "the collection date"

The first design used each video's `last_fetched_at`. The code review showed why that is wrong for a card like this:

- `last_fetched_at` is **one shared value per video**, overwritten whenever **anyone** re-fetches it. Another researcher's run would move your project's dates, and reveal their activity.
- it only keeps the **latest** fetch, so "collected from" would not be when your project first collected.

So the dates come from `discovered_at` on **this project's** run-video links: when your runs actually found each video. `last_fetched_at` keeps its own job, which is starting the 30-day retention clock for the purge (US-040).

## File-by-file explanation

### `src/api/core/views.py` and `src/api/core/urls.py`

`ResultsSummaryView`, with GET only, routed as `project-results-summary`. It finds the project through `get_project()`, so another owner's project is a `404`.

### `src/api/core/tests.py`

`ResultsSummaryApiTests` covers:

- the counts, including a video in two runs and comments split by level
- the date range
- another project of the same owner, with a channel and a reply that must not leak
- another owner sharing a video and re-fetching it later, which must not change your dates
- an empty project
- foreign and unknown projects (`404`)
- writes (`405`)

### `src/ui/src/apiClient.ts` and `src/ui/tests/resultsSummaryApi.test.ts`

The `ResultsSummary` type, a guard that checks the JSON shape, and `getResultsSummary`. They are tested with `fetch` faked.

### `src/ui/src/App.tsx` and `src/ui/src/App.css`

The Results panel and its card. Loading follows the same late-response guards as the other panels (an `AbortController` held in a ref, an identity check, and the project id). A summary that arrives after you switched project is never shown.

## How the pieces connect

```text
Results panel (active project P)
   '-- getResultsSummary(P)  on project change, Refresh, and after Start run
          GET /api/projects/P/results/summary/
             get_project()  -> 404 unless P is yours
             runs                 = P's collection runs
             videos, channels     = through P's run-video links       (distinct)
             comments, replies    = through P's run-comment links     (split by level)
             statistics_snapshots = P's runs' snapshots
             first/last           = min/max discovered_at of P's run-video links
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

Passing looks like `OK` (226 tests), `pass 64`, a finished build and no lint output. The curl command for the endpoint is in [commands.md](commands.md).

## How to test manually

1. Make sure your database is up to date. `./run-local.sh` migrates SQLite on start. With Compose PostgreSQL, run `DATABASE_ENGINE=postgresql venv/bin/python manage.py migrate` from `src/api` first.

2. `cd src && ./run-local.sh`, open `http://localhost:5173/`, and pick a project that has a collected run (see page 23 for collecting with comments).

3. The Results card shows the counts and "Data collected between …".

4. Compare with `http://127.0.0.1:8000/admin/`. The run count matches the project's Collection runs. Videos match its Collection run videos (each video once). Comments and replies match its Collection run comments, split by level.

5. Start a new run. The card's Runs count goes up by one right away.

## Common errors

- **`relation "youtube_videos" does not exist`.** The database you are using is behind on migrations. Run `manage.py migrate` against it (see step 1).

- **The card says "No data collected yet" but runs exist.** The runs are still `pending`, or found nothing. Run `collect_runs`, then click Refresh.

- **The numbers look lower than the admin's totals.** The admin shows every project's and every owner's rows. The card shows only the active project's.

## Known gaps

- No processed counts yet: cleaning (US-024) and sentiment (US-025) add them when they exist.

- The card has no automated render test (there is no React test setup yet). The manual check above covers it.
