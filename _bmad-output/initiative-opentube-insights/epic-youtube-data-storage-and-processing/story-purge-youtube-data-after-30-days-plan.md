---
title: 'Purge YouTube data after 30 days'
type: 'feature'
ticket: '6'
created: '2026-10-07'
status: 'built'
baseline_revision: '09ba60326c170110a7d8cfe6d9d5406918fb79c8'
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

**Problem:** The YouTube API Services Developer Policies (III.E.4.d) allow API data to be stored for at most 30 days. Nothing deletes it, so every stored dataset eventually breaks the policy (US-040). US-023 also handed its "comments and replies are covered by the purge" proof to this story.

**Approach:** Add a management command, `manage.py purge_youtube_data`. It deletes the YouTube data rows whose fetch or capture time is older than 30 days, as `docs/database_schema.md` defines. It keeps all researcher-authored and collection-metadata rows and records the purge date on the affected runs. `--dry-run` reports what would be deleted without deleting.

## Boundaries & Constraints

**Always:**
- **Cutoff:** `now - 30 days`, from one `RETENTION_DAYS = 30` constant read once per command run. A row exactly at the cutoff is kept; only strictly older rows are deleted.
- **What is deleted, with the policy timestamp:**
  - `YouTubeChannel` by `last_fetched_at`.
  - `YouTubeVideo` by `last_fetched_at`. Its `CollectionRunVideo` links, `VideoStatisticsSnapshot`s and `YouTubeComment`s go with it by `CASCADE`.
  - `YouTubeComment` by `last_fetched_at`. Its replies (`parent_comment` `CASCADE`) and `CollectionRunComment` links go with it.
  - `VideoStatisticsSnapshot` by `captured_at`.
- **Channel side effect:** deleting a channel leaves its videos with `channel` null (`SET_NULL`, US-018). Nothing else changes on those videos.
- **What is kept:** `research_projects`, `saved_queries`, `collection_runs` (with every counter unchanged) and `api_request_logs`. `effective_params` is kept too: it holds the researcher's query, not YouTube data.
- **Atomicity:** the deletes and the `data_purged_at` stamping run in one `transaction.atomic()`, so a crash leaves nothing half-purged.
- **Output:** one line per deleted kind with its count (cascades included), plus the number of runs stamped. `--dry-run` prints the same counts and changes nothing.
- **Tests:** no network. Use controlled timestamps (rows created, then their time fields set with `update()`). Validated on Compose PostgreSQL, where the cascades are real database behavior.

**Decisions** (approved by the human on 2026-10-07):
- **Run stamping:** a run's `data_purged_at` is set to the command's `now` when the purge removes its **last** link. Concretely: after the deletes, inside the same transaction, every run with `data_purged_at` null that had at least one `CollectionRunVideo` or `CollectionRunComment` link before the purge, and has none after, is stamped.
- **Not stamped:** a run that keeps any link (for example, a later run refreshed its videos), a run that never had links, and a run already stamped. Dry-run stamps nothing; it reports how many runs would be stamped.

**Never:**
- No scheduler or cron set-up: running the command on a schedule is an operator decision, documented in commands.md.
- No `derived_metrics` / sentiment / processing tables: they do not exist yet, and the stories that add them extend this command.
- No `--days` option: the window is policy, not configuration.
- No deletion of request logs or runs.
- No UI change: US-016 already shows "Data purged on <date>".
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Old video | video fetched 31 days ago, with links, 1 snapshot and 2 comments (1 with a reply) | the video, its links, snapshot, comments and reply are deleted; the run, its counters and its request logs are kept | No error expected |
| Fresh video | video fetched 29 days ago | kept with everything attached | No error expected |
| Boundary | `last_fetched_at` exactly at the cutoff | kept | No error expected |
| Old channel | channel fetched 31 days ago; its video fetched today | channel deleted; video kept with `channel` null | No error expected |
| Old snapshot on a fresh video | snapshot captured 31 days ago, video fresh | snapshot deleted; video kept | No error expected |
| Old comment on a fresh video | comment fetched 31 days ago with a fresh reply | comment and its reply deleted; video kept | No error expected |
| Run fully purged | run 1's only video is fetched 31 days ago | run 1 stamped `data_purged_at` = now; counters and logs unchanged | No error expected |
| Run partly kept | run 1 and run 2 share video V; run 2 refreshed V today; run 1's other video is old | run 1 keeps its V link, so it is not stamped; run 2 not stamped | No error expected |
| No links, already stamped | a run that never found anything, and a run with `data_purged_at` already set | neither is stamped or re-stamped | No error expected |
| Dry run | `--dry-run` with old data | counts printed; nothing deleted; no run stamped | No error expected |
| Nothing old | all data fresh | zero counts; nothing changes | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/purge.py` (new) -- `purge_youtube_data(*, now, dry_run) -> PurgeResult`, with `RETENTION_DAYS = 30`. The ORM `QuerySet.delete()` returns `(total, {model_label: count})`, so use it for the counts (cascades included). For dry-run, collect the same querysets and count them, including what would cascade (e.g. `Collector` from `django.db.models.deletion`, or explicit counts). The command and the function stay separate so tests call the function with a fixed `now`.
- `src/api/core/management/commands/purge_youtube_data.py` -- a thin command, as `collect_runs` is: the `--dry-run` flag, one call, and printing.
- `src/api/core/models.py` -- no schema change. `CollectionRun.data_purged_at` exists (US-010); check the `on_delete` rules listed above before relying on them.
- `src/api/core/tests.py` -- `PurgeYouTubeDataTests`: one test per matrix row, plus one command test (output and `--dry-run`).
- `docs/project-understanding/commands.md` (thesis repo, story-page commit) -- add the command, and say it should run at least daily.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/purge.py` -- the purge function.
- [x] `src/api/core/management/commands/purge_youtube_data.py` -- the command.
- [x] `src/api/core/tests.py` -- one test per matrix row plus the command.

**Acceptance Criteria:**
- Given the old-video test, when the video delete is removed, then the test fails.
- Given the boundary test, when `<` becomes `<=`, then the test fails.
- Given the dry-run test, when dry-run deletes, then the test fails.
- After a purge, every `ApiRequestLog` and `CollectionRun` row still exists and its run counters are unchanged.

## Implementation Notes

- Dry run performs the real deletes and stamping inside the same `transaction.atomic()` and then calls `transaction.set_rollback(True)`, instead of a `Collector`. Counts are exact by construction (same code path), at the cost of holding the purge's row locks for the dry run's duration. Marked with a `ponytail:` comment in `core/purge.py`.
- Output prints all six deleted kinds in a fixed order (`core.YouTubeChannel`, `core.YouTubeVideo`, `core.CollectionRunVideo`, `core.VideoStatisticsSnapshot`, `core.YouTubeComment`, `core.CollectionRunComment`), zeros included, then `core.CollectionRun: stamped N`; dry run says `would delete` / `would stamp`.
- Delete order is channels, videos, comments, snapshots, so a comment or snapshot of an old video is counted once, under the video's cascade.
- Acceptance mutations checked on Compose PostgreSQL: removing the video delete fails 5 tests, `<` to `<=` fails the boundary test, dry run without rollback fails 2 tests.
- `docs/project-understanding/commands.md` not yet updated: it belongs in the story-page commit after review.

- Orchestrator check: 238 OK on PostgreSQL, migrations clean. Thesis baseline `87e2c2fad13cedba48c05b1e58fcb0cad4061a29`.

- Review patches (pass 1) applied: non-vacuous runs/logs assertion over all seven counters; comment-only-link stamping tests; `RETENTION_DAYS + 1` in the command test. The concurrency rule is documented in commands.md and the story page. Full suite 240 OK on PostgreSQL.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 3, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| A purge concurrent with `collect_runs` can delete a just-refreshed video (Django's collector selects PKs, then deletes by PK, with no re-check or lock) or abort on an FK violation from a new link | medium | patch (docs) | Confirmed in Django's deletion collector; the abort path rolls back cleanly. Both commands are operator-run on a single-user local tool, so the fix is the operating rule rather than locks: commands.md and the story page say not to run the purge while `collect_runs` runs. Also corrects a plan statement: the cascades are Django's `on_delete=CASCADE` (collector), not database `ON DELETE CASCADE` — noted here because the line is frozen. |
| `assert_runs_and_logs_kept` passes vacuously if runs are deleted, and checks only 2 of 7 counters | low | patch | Confirmed; assert the pre-purge ids and all seven counters. |
| The comment-link half of the stamping rule is untested | low | patch | Confirmed: dropping `run_comments` from either filter passes every test. Add comment-only-link runs (stamped and not stamped). |
| `test_command_prints_counts_and_dry_run_keeps_data` hardcodes 31 days | low | patch | Direct correction to `RETENTION_DAYS + 1`. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.

**Manual checks:**
- `venv/bin/python manage.py purge_youtube_data --dry-run` on the local database prints zero or more counts and changes nothing. In the Django shell, set one video's `last_fetched_at` 31 days back, run the command without `--dry-run`, and confirm in `/admin/` that the video, its links and comments are gone while the run and its logs remain.
