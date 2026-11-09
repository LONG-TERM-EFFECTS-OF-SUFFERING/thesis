---
title: 'US-046 Purge YouTube data automatically'
type: 'feature'
ticket: ''
created: '2026-11-08'
status: 'ready-for-dev'
baseline_revision: ''
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
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
- `src/docker-compose.yml` -- move the `api` environment to `x-api-env: &api-env` and use `<<: *api-env` in `api`. Add a `purge` service with `build: ./api`, the same environment, `depends_on: api: condition: service_healthy`, and `command: sh -c "while true; do python manage.py purge_youtube_data || true; sleep 3600; done"`. The command stays a literal; it is not an env value. This file is tracked in the **thesis** repo, so commit it there.
- `src/run-local.sh` -- add a third background job to `pids`, `( cd "$root/api"; export DATABASE_ENGINE=...; while true; do sleep 3600; "$python_bin" manage.py purge_youtube_data || true; done ) &`. It sleeps first so the API subshell's `migrate` finishes. This file is tracked in the thesis repo too (check with `git ls-files src/run-local.sh` before committing).
- `docs/project-understanding/commands.md` (30-day purge section) and `26-purge-youtube-data-after-30-days.md` ("run it at least once a day", "not while `collect_runs` is running") -- update after review.

## Tasks & Acceptance

**Execution:**
- [ ] `purge_youtube_data.py` -- the `running` guard and the skip message -- so the purge never overlaps a collection that is in progress.
- [ ] `test_purge.py` -- a skip test; delete the guard and confirm the test fails.
- [ ] `docker-compose.yml` -- the env anchor and the `purge` service.
- [ ] `run-local.sh` -- the hourly background loop.

**Acceptance Criteria:**
- Given `docker compose up`, when the stack is healthy, then the `purge` service logs one purge result every hour without anyone running a command.
- Given a run in `running`, when a pass fires, then nothing is deleted and the next pass an hour later purges normally.

## Design Notes

Why a loop and not a thread in the API (the US-044 pattern): Gunicorn runs 2 workers, so a thread per worker would purge twice, and `AppConfig.ready()` also fires for `migrate`, tests and every command. The loop runs one process with no locking, and it reuses a command that is already tested.

Known ceiling (`ponytail:` comment next to the guard): the check and the purge are not atomic, so a run that starts in between can still overlap. The consequences are the ones page 26 describes (a refreshed video can be deleted, or the purge rolls back), with no corruption. Upgrade path: a PostgreSQL advisory lock shared by `collect_run` and the purge. A run left `running` after a crash (US-044 ceiling) blocks every purge until it is resolved; that shows in the log as one skip line per hour.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test core.tests.test_purge` -- expected: pass, including the new skip test.
- `cd src/api && venv/bin/python manage.py test` and `makemigrations --check --dry-run` -- expected: all pass, `No changes detected`.
- `cd src && docker compose config --quiet` -- expected: exit 0. Then `docker compose config` shows `purge` with the same environment as `api`.
- `bash -n src/run-local.sh` -- expected: no syntax errors.

**Manual checks (if no CLI):**
- `cd src && docker compose up -d && docker compose logs purge` -- the first pass prints the per-kind counts, or the skip line.
