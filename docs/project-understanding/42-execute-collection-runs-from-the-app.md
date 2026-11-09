# 42 - Execute collection runs from the app

Story: US-044, Execute collection runs from the app.

Status note: this page describes US-044 after two review passes on 2026-11-08 and their fixes. The story came from the thesis review; see `docs/thesis-review-app-changes.md`.

## What this story changed

Before, **Start run** only created a `pending` run, and nothing happened until an operator ran `manage.py collect_runs`. Now:

1. **Start run** creates the `pending` run and returns `201` at once, as before.
2. After the row is committed, the API hands the run to a **background thread** in its own process. The thread calls the same `collect_run` as before: collection, then normalization, then sentiment when a model is configured.
3. The **Runs** table reloads every 3 s while any run of the active project is `pending` or `running`. When a run that was active finishes, **Results** reloads once.
4. Without `YOUTUBE_API_KEY`, Start run returns `503` (`YOUTUBE_API_KEY is not configured.`) and creates no run.

`collect_runs` still exists. It is now a recovery tool for runs left `pending`.

## Why

The tool's users are researchers, not server operators. Asking them to run a backend command after every click made the app unusable without a developer at hand.

## Why a thread, and not inside the request or a queue

- **Inside the request** would block the browser for the whole collection, and Gunicorn kills a request after 60 s (`GUNICORN_TIMEOUT`). A thread lets the request return at once.
- **A job queue** (Celery, RQ) needs a broker such as Redis and a worker container. That is too much for a local research tool.
- **A Compose worker that loops `collect_runs`** needs no Python, but it does not cover `run-local.sh`, and it is still a backend command.

## Files

**API (`src/api`):**
- `core/collection.py`: `collect_run_in_background(run_id, api_key)` starts a daemon thread. `_collect_in_thread` loads the run, calls `collect_run`, logs anything unexpected and closes the thread's database connections in a `finally`.
- `core/views.py`: `CollectionRunStartView.post` checks the key, creates the run, then calls `transaction.on_commit(...)` so the thread never looks for a row that is not committed yet.
- `opentube_insights_api/settings.py`: SQLite now uses `transaction_mode: IMMEDIATE` and a 20 s timeout. Two run threads writing at once would otherwise fail with "database is locked". PostgreSQL does not need this.
- `core/management/commands/collect_runs.py`: unchanged, except for its docstring.

**UI (`src/ui`):**
- `src/App.tsx`: the polling effect. It goes through `latestRequest` like every list load.
- `src/collectionRunState.ts`:
  - `isActiveRun` (the run is `pending` or `running`)
  - `hasNewlyFinishedRun` (Results reloads when a run that was active is not active any more, even while another run is still active)
- `src/RunsSection.tsx`:
  - The live region now holds only the loading, error and empty messages, so screen readers are not told the climbing counts every 3 s.
  - When the open run's row status changes, a **Reload details** notice appears.
- `src/QueriesSection.tsx`: the card says **Run started** with a link to Runs, instead of a status frozen at `pending`.
- `src/ResultsSection.tsx`: when there is no sentiment yet, the empty sentiment area explains that sentiment is computed after a run completes, and that Apply checks again.

## The subtle parts

- **`completed` means collection is done, not analysis.** The run turns `completed` first. Normalization and sentiment then run in the same thread. With a local model, sentiment can take minutes, so Results may reload before sentiment exists. That is why the hint above exists. This was a deliberate choice (the human decided it in review), to keep the documented meaning of `status` and `finished_at`.
- **`on_commit` and its test.** Without `ATOMIC_REQUESTS`, Django runs an `on_commit` callback immediately. The test therefore posts the start inside `transaction.atomic()` and checks that the thread has not started before the block ends. Without that, the test would still pass with `on_commit` deleted.
- **Known limits** (marked `ponytail:` in the code):
  - If the API process dies mid-run (container stop, `runserver` reload), the run stays `running` forever.
  - A run left `pending` stays pending until `collect_runs` runs.
  - In both cases the UI keeps polling that project every 3 s.
  - Researcher-started runs can now overlap a scheduled purge (deferred-work entry).

## Commands

```bash
cd src/api && venv/bin/python manage.py test        # 395 tests
cd src/ui && npm test && npm run build              # 114 tests, typecheck
cd src/api && venv/bin/python manage.py collect_runs # only for runs left pending
```

## How to test manually

1. Put a real `YOUTUBE_API_KEY` in `src/.env`, then run `docker compose up --build` from `src`.
2. In **Queries**, click **Start run** on a saved query. The card says **Run started**.
3. Open **Runs**. The row goes `pending` → `running` → `completed` without Refresh, and the request and quota counts climb.
4. Open **Results**. The counts update when the run completes. If a sentiment model is configured, click **Apply** after a while to see the sentiment chart.
5. Remove the key and restart. Start run then shows `YOUTUBE_API_KEY is not configured.` and no row appears.

## Common errors

- **A run stays `running` forever.** The API restarted mid-run. There is no automatic recovery yet. The row is harmless, but its project keeps polling.
- **A run stays `pending`.** It was started before US-044, or the API stopped before the thread began. Run `collect_runs` once.
- **`OperationalError: database is locked`** on SQLite. Check that `settings.py` still sets the SQLite `OPTIONS` above.
