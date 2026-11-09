# 44 - Purge YouTube data automatically

Story: US-046, Purge YouTube data automatically.

Status note: this page describes US-046 after its two reviews of 2026-11-08. The story came from the thesis review; see `docs/thesis-review-app-changes.md`.

## What this story added

The 30-day purge from US-040 (page 26) now runs by itself every hour. Nobody has to run `purge_youtube_data`.

- **Compose:** a new `purge` service runs the command, sleeps an hour, and repeats. It starts once `api` is healthy, so the migrations have run.
- **`run-local.sh`:** a background job waits 60 s for the API's `migrate`, then runs the same purge-then-sleep loop.

A failed pass (for example, the database is down) never stops the loop. The error stays in the log, and the next pass is an hour later.

## The command now skips during a collection

Since US-044, a researcher can start a run at any time, so nobody can keep the purge and a collection apart by hand any more. `purge_youtube_data` therefore checks first: if any collection run is `running`, it prints `Skipped: a collection run is running.`, deletes nothing and exits normally. `--dry-run` skips the same way. The next pass, an hour later, purges normally.

## Files

- `src/api/core/management/commands/purge_youtube_data.py`: `Command.handle` holds the `running` check. `core/purge.py` and `RETENTION_DAYS` are unchanged.
- `src/api/core/tests/test_purge.py`: `test_command_skips_while_a_collection_run_is_running` puts old data next to a `running` run, then checks that both the real pass and the dry run print only the skip line and keep every row.
- `src/docker-compose.yml`: the API settings moved to an `x-api-env` block. The `api` and `purge` services both pull it in with `<<: *api-env`, so the two cannot drift apart. `purge` needs the same settings, because Django's system checks (such as `SENTIMENT_MODEL`) run for every management command. `init: true` lets `docker compose stop` end the loop at once; without it, `sh` runs as process 1, ignores the stop signal, and Docker waits 10 s before killing it.
- `src/run-local.sh`: the third background job.

## Key concept: a shell loop, not a scheduler

A `while true; do …; sleep 3600; done` loop needs no new dependency. A thread inside the API, the pattern US-044 used, would be wrong here: Gunicorn runs two workers, so the purge would run twice, and Django starts apps for `migrate`, tests and every command too. The loop is one process, and it reuses a command that is already tested.

## Limits

- **The check and the purge are not atomic.** A run that starts between them can still overlap the purge. The effects are the ones page 26 describes (a freshly refreshed video can be deleted, or the purge rolls back), and nothing is corrupted. The fix, if it matters, is a PostgreSQL advisory lock shared with `collect_run`.
- **A run stuck in `running` blocks every purge.** When the process collecting a run dies (a container restart, or a `runserver` reload during a collection), the run stays `running` (page 42). Every pass then prints the skip line, and data older than 30 days stays. The admin shows `status` read-only, so for now the only way out is the Django shell (below). A stale-run sweep is in `deferred-work.md`.
- Stopping `run-local.sh` can leave an idle `sleep` process for up to an hour. It is harmless.

## Commands

From `src/api`:

```bash
venv/bin/python manage.py test core.tests.test_purge   # 16 tests, including the skip test
```

From `src`:

```bash
docker compose up --build -d
docker compose logs -f purge
```

The first pass runs as soon as `api` is healthy, and it really deletes data older than 30 days.

## How to test manually

1. `docker compose up --build -d`, then `docker compose logs purge`. You see one line per deleted kind, or the skip line.
2. Start a run in the app and, while it is `running`, run `docker compose exec api python manage.py purge_youtube_data --dry-run`. It prints the skip line.
3. `docker compose stop purge` returns at once, not after 10 s.

## Common errors

- **The log shows the skip line every hour and data is never purged.** A run is stuck in `running`. Find it in the admin, then mark it failed from `docker compose exec api python manage.py shell`, with `CollectionRun.objects.get(pk=<id>).transition_to("failed", error_message="Collector process died.")` (after `from core.models import CollectionRun`). `transition_to` also stamps `finished_at`.
- **`purge` exits at once with a system-check error.** It reads the same settings as `api`; fix the `.env` value the error names.
