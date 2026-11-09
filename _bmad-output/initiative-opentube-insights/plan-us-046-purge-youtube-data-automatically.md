---
title: 'US-046 Purge YouTube data automatically'
type: 'feature'
ticket: ''
created: '2026-11-08'
status: 'built'
baseline_revision: 'api=1254857134f1bbeeead0551e412c6645a6123dd0 thesis=8dcd428f664cec61b6a7071d38ff17da4c9edde1'
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

**Problem:** The 30-day purge required by the YouTube API Services Developer Policies (US-040) runs only when an operator runs `manage.py purge_youtube_data`. The thesis review asked for it to be automatic. Since US-044, researchers start runs whenever they like, so an operator can no longer follow the "never purge during a collection" rule by hand (see the US-044 entry in `deferred-work.md`).

**Approach:** Run the existing command every hour with a plain shell loop, so there is no scheduler library and no new Python scheduling code: a new Compose `purge` service built from the `api` image, and the same loop as a background job in `run-local.sh`. The command itself skips, with a message, while any collection run is `running`, so the loop retries an hour later instead of overlapping a collection.

## Boundaries & Constraints

**Always:**
- `purge_youtube_data` keeps its behavior and output when no run is `running`, and `--dry-run` keeps working.
- The `purge` service shares the `api` service's environment through a YAML anchor, not a copied list, because system checks such as `core.E001` (`SENTIMENT_MODEL`) run for every management command.
- The `purge` service starts only after `api` is healthy, so migrations have run.
- One failed purge never stops the loop: `|| true` keeps it going, and the error stays in the container log.

**Never:**
- No cron, Celery beat, APScheduler or other dependency, and no thread in the API process.
- No change to `core/purge.py` deletion logic or to `RETENTION_DAYS`.
- No edits to `content/*.tex`. Follow-ups go in `docs/thesis-review-app-changes.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Idle app | no run `running`, data older than 30 days | the next hourly pass deletes it, with the same output as today | — |
| Collection in progress | some run `running` | prints `Skipped: a collection run is running.`, deletes nothing, stamps nothing, exits 0 | loop retries in an hour |
| Dry run during a collection | `--dry-run`, a run `running` | same skip message (no counts) | — |
| Purge error | e.g. database down | command exits non-zero, and the loop logs it and sleeps | `|| true` |

</frozen-after-approval>

## Code Map

- `src/api/core/management/commands/purge_youtube_data.py` `Command.handle` -- add the `running` check before `purge_youtube_data(...)`, using `CollectionRun.objects.filter(status=CollectionRun.RunStatus.RUNNING).exists()`.
- `src/api/core/purge.py` -- unchanged. `purge_youtube_data(now=, dry_run=)` is the entry point.
- `src/api/core/tests/test_purge.py` -- add a command test: with a `running` run and old data, `call_command` prints the skip line and every row survives. The existing command tests cover the idle path.
- `src/docker-compose.yml` -- move the `api` environment to `x-api-env: &api-env` and use `<<: *api-env` in `api`. Add a `purge` service with `build: ./api`, the same environment, `depends_on: api: condition: service_healthy`, and `command: sh -c "while true; do python manage.py purge_youtube_data || true; sleep 3600; done"`, and `init: true` so `docker compose stop` ends the loop at once (without an init process, `sh` is PID 1 and ignores SIGTERM, and every stop waits the 10 s grace period). The command stays a literal; it is not an env value. This file is tracked in the **thesis** repo, so commit it there.
- `src/run-local.sh` -- add a third background job to `pids`, `( cd "$root/api"; export DATABASE_ENGINE=...; sleep 60; while true; do "$python_bin" manage.py purge_youtube_data || true; sleep 3600; done ) &`. The one-off `sleep 60` lets the API subshell's `migrate` finish; then the loop purges first and sleeps after, like the Compose loop, so a session shorter than an hour still purges. If `migrate` is still running, the first pass fails harmlessly and the next one is an hour later. This file is tracked in the thesis repo too (check with `git ls-files src/run-local.sh` before committing).
- `docs/project-understanding/commands.md` (30-day purge section) and `26-purge-youtube-data-after-30-days.md` ("run it at least once a day", "not while `collect_runs` is running") -- update after review.

## Tasks & Acceptance

**Execution:**
- [x] `purge_youtube_data.py` -- the `running` guard and the skip message -- so the purge never overlaps a collection that is in progress.
- [x] `test_purge.py` -- a skip test; delete the guard and confirm the test fails.
- [x] `docker-compose.yml` -- the env anchor and the `purge` service.
- [x] `run-local.sh` -- the hourly background loop.

**Acceptance Criteria:**
- Given `docker compose up`, when the stack is healthy, then the `purge` service logs one purge result every hour without anyone running a command.
- Given a run in `running`, when a pass fires, then nothing is deleted and the next pass an hour later purges normally.

## Plan Change Log

- **Loop 1 (2026-11-08), from review pass 1 finding 2 (bad_plan).**
  - **Trigger:** the Code Map told `run-local.sh` to sleep an hour before the first pass, so a `./run-local.sh` session shorter than an hour never purges. That leaves the 30-day deletion depending on long sessions, which is the problem the intent removes.
  - **Amended:** the `run-local.sh` Code Map line now has a one-off `sleep 60`, then purge-then-sleep. The `docker-compose.yml` line gained `init: true` (pass 1 finding 1, patch). The Known-ceiling note now says the `ponytail:` comment names both cases (pass 1 finding 3a, patch).
  - **Known-bad state avoided:** a local loop that sleeps 3600 s before its first purge.
  - **KEEP (from `us046-pass1-api.patch` and `us046-pass1-thesis.patch` in the session scratchpad; reuse them, do not re-invent):**
    - the guard in `Command.handle` (`CollectionRun.objects.filter(status=CollectionRun.RunStatus.RUNNING).exists()`), the exact skip line, the early `return`, and the extended docstring
    - the skip test `test_command_skips_while_a_collection_run_is_running`, which loops over `()` and `("--dry-run",)` and asserts row counts, `data_purged_at`, and `assert_runs_and_logs_kept`
    - the top-level `x-api-env: &api-env` anchor with both comments kept, `<<: *api-env` in `api` and `purge`, the `purge` service comment, `build: context: ./api`, the `command`, and `depends_on: api: condition: service_healthy`
    - the `run-local.sh` job's comment, `cd`, `DATABASE_ENGINE` default, `|| true` and `pids+=("$!")`, with only the sleep order changed
  - All of these passed `test_purge` on SQLite and PostgreSQL, the full suite (396), `compose config`, and `bash -n`.
  - **Never** run `purge_youtube_data` without `--dry-run` against `src/api/db.sqlite3` or Compose PostgreSQL to check the loop. Pass 1 did, and it deleted the human's local dev data. Check the loop with `bash -n`, or with the command swapped for `echo`.

## Review Triage Log

Pass 1 (quick), 4 findings: 1 medium, 2 low, 1 medium with a low part split off, 0 false. Routed bad_plan, so the code was reverted and saved as `us046-pass1-{api,thesis}.patch` in the session scratchpad.

- **low, patch (re-apply).** `purge` runs `sh -c` as PID 1, which ignores SIGTERM, so every `docker compose stop` or `down` waits the 10 s grace period and then sends SIGKILL. The reviewer measured 10.2 s with the same loop in `python:3.14-slim`. A killed pass rolls back inside `transaction.atomic()`. Fix: `init: true`.
- **medium, bad_plan.** `run-local.sh` sleeps 3600 s before the first purge, so a session shorter than an hour never purges. The human's `db.sqlite3` held rows older than 30 days, so the local path does keep real data. The plan's Code Map prescribed sleep-first.
- **low, patch (re-apply).** The `ponytail:` comment next to the guard names only the check/purge race. The plan's Known-ceiling note also names the stuck-run case (a run left `running` blocks every purge), and that is now recorded nowhere in code. Fix: name both cases in the comment.
- **medium, defer.** A run left `running` by a dead thread (`runserver` autoreload, container restart: the US-044 ceiling) blocks every purge indefinitely. `CollectionRunAdmin` has `status` read-only, no view or command fails a run, and `collect_runs` picks up only `pending`, so only a Django shell `.update()` clears it. The intent chose "skip while any run is `running`" and the plan accepted the ceiling, but the way out is the US-044 stale-run sweep, which this story does not build. Logged in `deferred-work.md`. The reviewer's sub-point that the skip line should name the run is rejected: the frozen matrix fixes the exact message.
- **low, reject.** A second `build: ./api` gives `purge` its own image (`src-purge`), so `docker compose build api` alone leaves `purge` on old code. The documented command, `docker compose up --build` (`commands.md`), rebuilds both. A shared image needs `image:` plus `pull_policy` on two services, which is more than a direct correction for a path nobody documents.

Pass 2 (quick), 1 finding: 1 low, 0 false. All pass-1 patches and the Loop 1 amendments are present; nothing repeats a pass-1 row.

- **low, reject.** The purge subshell in `run-local.sh` cannot `exec`, so `cleanup`'s SIGTERM kills the subshell and orphans its foreground child. The reviewer reproduced a stray `sleep` living on after shutdown. The outcome is real but invisible: one idle `sleep` for up to an hour, or a pass that is already running finishes and commits deletions the policy requires anyway. The fix needs a background `sleep` plus `wait` and a `TERM` trap, which is more than a direct correction for a defect nobody meets in everyday use.

## Design Notes

Why a loop and not a thread in the API (the US-044 pattern): Gunicorn runs 2 workers, so a thread per worker would purge twice, and `AppConfig.ready()` also fires for `migrate`, tests and every command. The loop runs one process with no locking, and it reuses a command that is already tested.

Known ceiling (`ponytail:` comment next to the guard, naming both cases below): the check and the purge are not atomic, so a run that starts in between can still overlap. The consequences are the ones page 26 describes (a refreshed video can be deleted, or the purge rolls back), with no corruption. Upgrade path: a PostgreSQL advisory lock shared by `collect_run` and the purge. A run left `running` after a crash (US-044 ceiling) blocks every purge until it is resolved; that shows in the log as one skip line per hour.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test core.tests.test_purge` -- expected: pass, including the new skip test.
- `cd src/api && venv/bin/python manage.py test` and `makemigrations --check --dry-run` -- expected: all pass, `No changes detected`.
- `cd src && docker compose config --quiet` -- expected: exit 0. Then `docker compose config` shows `purge` with the same environment as `api`.
- `bash -n src/run-local.sh` -- expected: no syntax errors.

**Manual checks (if no CLI):**
- `cd src && docker compose up -d && docker compose logs purge` -- the first pass prints the per-kind counts, or the skip line.
