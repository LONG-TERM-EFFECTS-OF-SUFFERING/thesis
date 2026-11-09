---
title: 'US-044 Execute collection runs from the app'
type: 'feature'
ticket: ''
created: '2026-11-08'
status: 'done'
baseline_revision: 'api=d6f729076fe861044e2d02aaad099595fcb2e0e7 ui=e162b3aa4073d07aaf389d9fb1193e8725387c96'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 1
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** "Start run" only creates a `pending` run. Nothing collects it until an operator runs `manage.py collect_runs`, which the tool's target users (researchers, not operators) cannot be expected to do. The thesis review asked for runs to execute from the app itself.

**Approach:** After the start endpoint commits a run, it hands the run to a background thread in the API process, which runs the existing `collect_run`. The web request still returns `201` immediately, so the Gunicorn timeout is not involved. The UI polls the run list while any run of the active project is `pending` or `running`. `collect_runs` stays as a recovery tool for runs left `pending`.

**Decision (human, 2026-11-08, after review pass 1):** for the UI, a run is finished when collection ends (`completed` or `failed`). Normalization and sentiment then keep running in the same thread, and that is accepted. Results reloads once at collection end, and while no sentiment pass exists, the empty sentiment area says that sentiment is computed after a run completes, when a model is configured, and that Apply checks again. The run's `status` and `finished_at` keep their documented meaning.

## Boundaries & Constraints

**Always:**
- Start the thread from `transaction.on_commit`, so the thread never looks up a row that is not committed yet.
- The thread closes its own database connections when it finishes (`django.db.connections.close_all()` in a `finally`).
- A missing `YOUTUBE_API_KEY` rejects the start with `503` and creates no run, matching `collect_runs`, which also refuses with no key.
- Every UI fetch that writes React state goes through `latestRequest` (AGENTS.md pitfall).
- No test reaches `googleapis.com`.

**Never:**
- No new dependency: no Celery, RQ, Redis or django-q. No new Compose service, no model or migration change.
- Do not delete `collect_runs`: `test_workflow.py` and the docs use it, and it collects runs left `pending`.
- Do not edit `content/*.tex`. Thesis follow-ups go in `docs/thesis-review-app-changes.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Start with key | valid saved query, key set | `201` `pending`; after commit a thread runs `collect_run(run, api_key=key)` | `collect_run` already records failures on the run |
| Start without key | `YOUTUBE_API_KEY` empty | `503` `{"detail": "YOUTUBE_API_KEY is not configured."}`, no run row | UI shows it in the card's error line |
| Invalid stored params | key set, params fail validation | `400`, unchanged from today, no thread | — |
| Thread crashes outside `collect_run` | e.g. run deleted before the thread looks it up | logged with `logger.exception`, connection closed | run stays as it was |
| UI with active runs | list has a `pending` or `running` run | list reloads every 3 s until none is active, then results reload once; an empty sentiment area shows the still-computing hint | a failed poll shows the list error, as Refresh does |

</frozen-after-approval>

## Code Map

- `src/api/core/views.py` `CollectionRunStartView.post` -- adds the key check (before the query lookup is fine; it needs no data) and an `on_commit` hook after `CollectionRun.objects.create`.
- `src/api/core/collection.py` -- add `collect_run_in_background(run_id, api_key)`, which starts a `threading.Thread` whose target loads the run, calls `collect_run`, logs any exception and closes connections. It sits beside `collect_run`, which stays unchanged.
- `src/api/core/management/commands/collect_runs.py` -- unchanged. Update its module docstring to say it is now for recovery.
- `src/api/core/tests/test_views.py` `CollectionRunStartApiTests` (`APITestCase`, so `on_commit` never fires in it) -- needs `@override_settings(YOUTUBE_API_KEY=...)` on the class, plus a new no-key `503` test.
- `src/api/core/tests/test_workflow.py` -- an `APITestCase` that already sets the key, so `on_commit` does not fire and `collect_runs` still collects. No change.
- `src/ui/src/App.tsx` -- owns `runList`, `loadRuns` (through `latestRequest`) and `resultsReloads`. The polling effect goes here.
- `src/ui/src/QueriesSection.tsx` -- the card shows `Run {status}` after a start, which stays correct. The error line already shows any start error.
- `src/api/opentube_insights_api/settings.py` `build_database_config` -- the SQLite branch gets `"OPTIONS": {"transaction_mode": "IMMEDIATE", "timeout": 20}`, so two run threads wait for each other instead of raising "database is locked". `core/tests/test_settings.py` checks the SQLite `ENGINE` and `NAME` keys separately, so adding OPTIONS breaks no assertion; add one assertion for it.
- `src/ui/src/ResultsSection.tsx` (~line 250, "No sentiment results yet") -- add the still-computing hint here. `Apply` (`handleApplyResultsFilters`) already refetches.
- `src/ui/src/collectionRunState.ts` -- add `isActiveRun(run)` (pending or running) and test it in `tests/collectionRunState.test.ts`. `App.tsx` imports it.
- `docs/project-understanding/commands.md` (lines 229–241), `16-…md` (lines 38, 140), `25-…md` (line 128) -- they say nothing collects runs automatically, and need updating after review.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/collection.py` -- add `collect_run_in_background` -- one place that owns the thread and the connection cleanup.
- [x] `src/api/core/views.py` -- in `CollectionRunStartView.post`, return `503` when the key is empty, and call `transaction.on_commit(partial(collect_run_in_background, run.pk, key))` after the create -- runs execute without an operator.
- [x] `src/api/core/tests/test_views.py` -- set the key on `CollectionRunStartApiTests`, add the `503` test (no run row), and add a `TransactionTestCase` that posts a start with `core.collection.collect_run` patched to record its run id, key and thread, then waits on an `Event` (5 s): the patched function must get the new run's id and the key, in a thread other than the main one -- this proves the thread really starts after commit.
- [x] `src/ui/src/App.tsx` -- add an effect: when the active project's `runList` is ready and has a `pending` or `running` run, `setTimeout(3000)` then `loadRuns`, with the timeout cleared on cleanup. When active runs drop to none after some were active, bump `resultsReloads` once -- the status updates without Refresh.
- [x] `src/api/core/management/commands/collect_runs.py` -- docstring only.

**Acceptance Criteria:**
- Given a configured key, when a researcher clicks Start run, then the run goes `pending → running → completed` with no command, and the Runs table shows each status without clicking Refresh.
- Given no key, when Start run is clicked, then the card shows an error naming `YOUTUBE_API_KEY` and no run appears.
- Given a run left `pending` (the process died before the thread started), when `collect_runs` runs, then it collects that run, as today.

## Design Notes

A thread inside the Gunicorn worker is the smallest choice that keeps everything in "the app". A Compose `worker` service looping `collect_runs` would need no Python, but it would not cover `run-local.sh`/`runserver`, and it is still a backend command. A job queue was already rejected in the thesis (it needs a broker).

Known ceiling (mark it with a `ponytail:` comment in both `collect_run_in_background` and the `App.tsx` effect, naming both cases): (1) when the worker process dies mid-run (container stop, `runserver` reload), the run stays `running` forever, which is the same as a `collect_runs` killed today. (2) Any run left `pending`, including every run started before US-044 and any whose thread failed before claiming it, stays pending until an operator runs `collect_runs`. In both cases the UI keeps polling that project every 3 s. Upgrade path: a stale-run sweep or a real queue.

KEEP from pass 1 (`us044-pass1-api.patch` and `us044-pass1-ui.patch` in the session scratchpad; reuse them, do not re-invent): `collect_run_in_background` plus `_collect_in_thread` (daemon thread, `logger.exception`, `connections.close_all()` in `finally`), the `503` check placed after `get_owner()`, `on_commit(partial(...))`, `@override_settings` on `CollectionRunStartApiTests`, the `APITransactionTestCase` with a patched `core.collection.collect_run` and an `Event`, `loadRuns(..., onLoaded)` with the results bump inside the async callback (lint-clean), and `RUN_POLL_MS`. All of these passed on SQLite and PostgreSQL.

## Review Triage Log

Pass 1 (quick), 4 findings: 2 medium, 2 low, 0 false. Routed as intent_gap, so the code was reverted. The pass-1 code is saved as `us044-pass1-{api,ui}.patch` in the session scratchpad.

- **medium, intent_gap.** Results reload before normalization and sentiment finish. `collect_run` (`core/collection.py`) moves the run to `completed`, then runs `process_collection_run` and `analyze_comments` in the same thread. The frozen matrix row "then results reload once" fires on `completed`, so the sentiment charts (`ResultsSection`, `summary.sentiment`) stay empty until a manual Refresh. The intent never decided what "finished" means for analysis.
- **low, patch (re-apply after re-derivation).** The background-start test passes without `on_commit`. Settings have no `ATOMIC_REQUESTS`, so `on_commit` fires immediately in autocommit. Fix: post the start inside `transaction.atomic()` in the `APITransactionTestCase`, assert `collect_run` is not called before the block exits, and assert it is called after.
- **medium, patch (re-apply).** Overlapping runs on SQLite fail with `OperationalError: database is locked`. `build_database_config` sets no SQLite `OPTIONS`, `run-local.sh` defaults to `DATABASE_ENGINE=sqlite`, and the reviewer reproduced the error 3 of 3 times with two writer threads. Fix: SQLite `OPTIONS` `{"transaction_mode": "IMMEDIATE", "timeout": 20}`.
- **low, patch (re-apply).** The polling `ponytail:` comment in `App.tsx` names only runs stuck in `running`. Any run left `pending`, including runs started before US-044, also keeps the project polling until `collect_runs` runs. Fix: name both cases in the comment.

Pass 2 (quick), 4 findings: 2 medium, 2 low, 0 false. None repeats a pass-1 row, and all pass-1 patches were present. All four route to patch.

- **medium, patch.** `App.tsx` reloads Results only when the loaded list has no active run, so one stuck `pending` or `running` run (plan ceiling cases 1–2) blocks the reload forever, and an overlapping run delays the first run's reload. Fix: reload when any run that was active in the list the timer came from is no longer active, using a pure helper in `collectionRunState.ts` that is tested.
- **low, patch.** `RunsSection.tsx` keeps the open run detail on its one-time fetch, so its heading says `(pending)` while the polled row says `completed`. Fix: a render-only notice above `RunDetail` when the row's status differs from the ready detail's, with a button that calls `handleSelectRun`. No effect, so it cannot loop against a detail that is newer than the row.
- **low, patch.** The query card shows `Run {status}` from the 201 response, so it reads "Run pending" forever now that runs execute. Fix: a static "Run started" hint that links to Runs.
- **medium, patch.** `RunsSection.tsx` has `aria-live="polite"` around the polled table, so screen readers announce the climbing request and quota counts every 3 s. Fix: keep the live region on the loading, error and empty messages only.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test` -- expected: all pass, including the new `503` and background-thread tests.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.
- `cd src && docker compose up -d db` then run the backend suite against PostgreSQL, because the `TransactionTestCase` thread needs a real second connection. Expected: pass.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all clean.

**Manual checks (if no CLI):**
- With a real key in Compose, click Start run. Runs shows `pending` → `running` → `completed` with no Refresh, and Results updates when it finishes.
